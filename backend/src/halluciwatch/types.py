"""Core data types shared across HalluciWatch.

Everything here is a plain dataclass so that fingerprints, generations and risk
reports can be serialised to JSON without a schema library in the hot path.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Fingerprint",
    "Generation",
    "RiskReport",
    "Tier",
    "TokenLogprob",
]


DEFAULT_SYSTEM_PROMPT = (
    "Answer the question as briefly as possible. Give only the answer itself, "
    "with no explanation. Always give your best guess."
)
"""The prompt used for BOTH corpus generation and scoring.

It must be the same in both places. The features a detector learns from are a
property of the prompt that produced them: a prompt that invites "I don't know"
shifts the entropy and self-consistency distributions substantially, so a model
trained on best-guess answers and served on refusal-friendly ones is scoring a
distribution it never saw. That skew was live in this codebase until it was
caught - corpus generation used this prompt while the detector served with a
"say so plainly rather than guessing" variant, and honest refusals were landing
anywhere between 0.27 and 0.60 risk.

If you change this, rebuild the corpus and retrain. `load_detector` warns when
the stored training prompt and the serving prompt disagree.
"""


class Tier:
    """Signal cost tiers.

    The cascade escalates through these in order. The numbers are the measured
    marginal cost on the reference machine (Apple M1, llama3.2:1b, 60 tokens):

    ``SURFACE``  free - computed from text already in hand.
    ``TOKEN``    +5% wall-time with ``top_logprobs=0``, +80% with ``top_logprobs>=1``.
    ``SAMPLING`` K extra generations (K x cost).
    ``VERIFY``   one extra short generation.
    """

    SURFACE = "surface"
    TOKEN = "token"
    SAMPLING = "sampling"
    VERIFY = "verify"

    ALL = (SURFACE, TOKEN, SAMPLING, VERIFY)


@dataclass(slots=True)
class TokenLogprob:
    """One generated token together with its alternatives.

    ``top_logprobs`` holds the top-k alternatives *including* the chosen token,
    exactly as Ollama returns them. It is empty when the caller requested
    ``top_logprobs=0`` (the cheap path), in which case only ``logprob`` is known.
    """

    token: str
    logprob: float
    top_logprobs: list[tuple[str, float]] = field(default_factory=list)

    @property
    def surprisal(self) -> float:
        """Negative log-probability of the chosen token, in nats."""
        return -self.logprob

    @property
    def probability(self) -> float:
        return math.exp(self.logprob)

    def distribution(self) -> list[float]:
        """Renormalised probabilities over the returned top-k alternatives.

        Ollama returns only the top-k, so the mass does not sum to 1. We
        renormalise over the observed support, which makes the resulting entropy
        a *lower bound* on the true next-token entropy. That is the standard
        truncated-entropy estimator and it is monotone in the quantity we want.
        """
        if not self.top_logprobs:
            return []
        probs = [math.exp(lp) for _, lp in self.top_logprobs]
        total = sum(probs)
        if total <= 0:
            return []
        return [p / total for p in probs]

    def entropy(self) -> float:
        """Shannon entropy (nats) over the truncated top-k support."""
        dist = self.distribution()
        if not dist:
            return 0.0
        return -sum(p * math.log(p) for p in dist if p > 0)

    def margin(self) -> float:
        """p(top1) - p(top2) over the truncated support. 1.0 when unrivalled."""
        dist = self.distribution()
        if not dist:
            return 0.0
        if len(dist) == 1:
            return dist[0]
        top = sorted(dist, reverse=True)
        return top[0] - top[1]

    def top_probability(self) -> float:
        dist = self.distribution()
        return max(dist) if dist else self.probability


@dataclass(slots=True)
class Generation:
    """A single completion plus whatever signals the backend returned."""

    text: str
    model: str
    tokens: list[TokenLogprob] = field(default_factory=list)
    prompt_tokens: int = 0
    eval_tokens: int = 0
    total_duration_s: float = 0.0
    eval_duration_s: float = 0.0
    seed: int | None = None
    temperature: float = 0.0
    finish_reason: str | None = None
    raw: Mapping[str, Any] | None = None

    @property
    def has_logprobs(self) -> bool:
        return bool(self.tokens)

    @property
    def has_alternatives(self) -> bool:
        """True when top-k alternatives were requested (``top_logprobs>=1``)."""
        return bool(self.tokens) and bool(self.tokens[0].top_logprobs)

    @property
    def tokens_per_second(self) -> float:
        if self.eval_duration_s <= 0:
            return 0.0
        return self.eval_tokens / self.eval_duration_s

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "model": self.model,
            "n_tokens": len(self.tokens),
            "prompt_tokens": self.prompt_tokens,
            "eval_tokens": self.eval_tokens,
            "total_duration_s": round(self.total_duration_s, 4),
            "seed": self.seed,
            "temperature": self.temperature,
            "finish_reason": self.finish_reason,
        }


@dataclass(slots=True)
class Fingerprint:
    """A fixed-length, named feature vector describing one generation.

    Names are carried alongside values so a stored model can assert that the
    features it is asked to score are the ones it was trained on. Silent feature
    reordering is the classic way tabular pipelines rot.
    """

    names: list[str]
    values: list[float]
    tiers: list[str] = field(default_factory=list)
    cost_s: float = 0.0

    def __post_init__(self) -> None:
        if len(self.names) != len(self.values):
            raise ValueError(
                f"fingerprint length mismatch: {len(self.names)} names vs {len(self.values)} values"
            )

    def as_dict(self) -> dict[str, float]:
        return dict(zip(self.names, self.values, strict=False))

    def subset(self, tiers: Sequence[str]) -> Fingerprint:
        """Return only the features belonging to the given tiers."""
        if not self.tiers:
            return self
        keep = [i for i, t in enumerate(self.tiers) if t in tiers]
        return Fingerprint(
            names=[self.names[i] for i in keep],
            values=[self.values[i] for i in keep],
            tiers=[self.tiers[i] for i in keep],
            cost_s=self.cost_s,
        )

    def __len__(self) -> int:
        return len(self.values)


@dataclass(slots=True)
class RiskReport:
    """The user-facing result: a calibrated risk score plus its justification."""

    risk: float
    """Calibrated probability in [0, 1] that the answer is not supported."""

    decision: str
    """One of ``accept``, ``review``, ``reject``, ``abstain``.

    ``abstain`` means the model declined to answer. It is reported separately
    because a refusal asserts nothing, so a hallucination-risk score is not
    meaningful for it - and because refusals are excluded from training, making
    the classifier's output on them unreliable."""

    answer: str
    question: str
    model: str

    tiers_used: list[str] = field(default_factory=list)
    fingerprint: Fingerprint | None = None
    top_factors: list[tuple[str, float]] = field(default_factory=list)
    token_risk: list[tuple[str, float]] = field(default_factory=list)
    """Per-token (token, normalised surprisal) for the UI heat-map."""

    samples: list[str] = field(default_factory=list)
    clusters: list[list[str]] = field(default_factory=list)
    latency_s: float = 0.0
    overhead_s: float = 0.0
    calibrated: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk": round(self.risk, 4),
            "decision": self.decision,
            "answer": self.answer,
            "question": self.question,
            "model": self.model,
            "tiers_used": self.tiers_used,
            "top_factors": [(n, round(v, 4)) for n, v in self.top_factors],
            "token_risk": [(t, round(v, 4)) for t, v in self.token_risk],
            "clusters": self.clusters,
            "latency_s": round(self.latency_s, 4),
            "overhead_s": round(self.overhead_s, 4),
            "calibrated": self.calibrated,
            "notes": self.notes,
            "features": self.fingerprint.as_dict() if self.fingerprint else {},
        }

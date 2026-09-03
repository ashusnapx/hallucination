"""The detector: generate an answer, fingerprint it, score the risk.

The cascade
-----------
Signal families differ in cost by two orders of magnitude, and the expensive
ones are not uniformly better - they are better *on different questions*. So
rather than always paying for everything, the detector escalates:

1. **Tier 0-1** run on every request. They are computed from the generation the
   caller already wanted, so the marginal cost is the ``top_logprobs`` penalty
   and some arithmetic.
2. If the tier-1 risk lands in an **uncertainty band**, tier 2 runs: K extra
   samples, clustered by meaning. Outside the band the cheap signals are already
   decisive and sampling would only add latency.
3. **Tier 3** (self-verification) is opt-in; it is near-chance on small models.

The band is the whole point. On the pilot distribution roughly a third of
questions fall inside it, so the average cost is far below the worst case while
the hard questions still get the expensive treatment.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass

from .backends.ollama import RICH_TOP_LOGPROBS, OllamaBackend, OllamaOptions
from .calibration import DecisionPolicy
from .cluster import ClusterResult
from .features import (
    build_fingerprint,
    consistency_features,
    surface_features,
    token_features,
    verify_features,
)
from .types import DEFAULT_SYSTEM_PROMPT, Fingerprint, Generation, RiskReport, Tier

log = logging.getLogger(__name__)

__all__ = ["DetectorConfig", "HallucinationDetector"]

# Re-exported for backwards compatibility; the definition lives in types.py so
# corpus building and scoring cannot drift apart.
DEFAULT_SYSTEM = DEFAULT_SYSTEM_PROMPT


@dataclass
class DetectorConfig:
    """Knobs for the cascade. Defaults come from the pilot measurements."""

    model: str = "llama3.2:3b"
    embed_model: str = "nomic-embed-text"
    host: str = "http://localhost:11434"

    tiers: tuple[str, ...] = (Tier.SURFACE, Tier.TOKEN, Tier.SAMPLING)
    """Tiers this detector may use. Tier.VERIFY is excluded by default because
    it measured at chance on sub-3B models - see features/verify.py."""

    escalate_low: float = 0.20
    escalate_high: float = 0.80
    """Uncertainty band. Tier-1 risk inside [low, high] triggers sampling."""

    n_samples: int = 6
    sample_temperature: float = 1.0
    similarity_threshold: float = 0.92

    max_tokens: int = 128
    temperature: float = 0.0
    seed: int | None = 42
    top_logprobs: int = RICH_TOP_LOGPROBS

    system_prompt: str = DEFAULT_SYSTEM

    def sampling_enabled(self) -> bool:
        return Tier.SAMPLING in self.tiers

    def verify_enabled(self) -> bool:
        return Tier.VERIFY in self.tiers


class HallucinationDetector:
    """Score the hallucination risk of a locally-generated answer.

    Usage::

        det = HallucinationDetector.load("models/detector.json")
        report = det.score("Who discovered penicillin?")
        print(report.risk, report.decision)

    Without a trained model the detector still works: it falls back to a
    transparent heuristic over normalised token entropy and semantic entropy and
    marks the report ``calibrated=False``. That keeps the library usable
    immediately after install, while being explicit that the number is not a
    calibrated probability.
    """

    def __init__(
        self,
        backend: OllamaBackend | None = None,
        config: DetectorConfig | None = None,
        model: object | None = None,
        policy: DecisionPolicy | None = None,
        feature_names: Sequence[str] | None = None,
    ) -> None:
        self.config = config or DetectorConfig()
        self.backend = backend or OllamaBackend(
            model=self.config.model,
            host=self.config.host,
            embed_model=self.config.embed_model,
        )
        self.model = model
        self.policy = policy or DecisionPolicy()
        self.feature_names = list(feature_names) if feature_names else None

    # ------------------------------------------------------------------ scoring

    def score(
        self,
        question: str,
        *,
        answer: str | None = None,
        force_tiers: Sequence[str] | None = None,
    ) -> RiskReport:
        """Generate (unless ``answer`` is given) and score.

        ``force_tiers`` overrides the cascade, which is what the ablation
        harness uses to measure each tier in isolation.
        """
        started = time.perf_counter()
        notes: list[str] = []
        allowed = tuple(force_tiers) if force_tiers is not None else self.config.tiers

        prompt = self._build_prompt(question)

        generation = self._generate(prompt, answer)
        gen_done = time.perf_counter()

        values: dict[str, float] = {}
        tiers_used: list[str] = []

        # --- Tier 0: free ------------------------------------------------
        if Tier.SURFACE in allowed:
            values.update(surface_features(generation.text))
            tiers_used.append(Tier.SURFACE)

        # --- Tier 1: token distribution ----------------------------------
        if Tier.TOKEN in allowed:
            if not generation.has_logprobs:
                notes.append("no logprobs available; token-tier features are zero")
            values.update(token_features(generation))
            tiers_used.append(Tier.TOKEN)

        # --- Tier 2: sampling, only inside the uncertainty band -----------
        samples: list[str] = []
        clusters: ClusterResult | None = None
        if Tier.SAMPLING in allowed:
            cheap_risk = self._raw_score(values, (Tier.SURFACE, Tier.TOKEN))
            escalate = (
                force_tiers is not None
                or self.config.escalate_low <= cheap_risk <= self.config.escalate_high
            )
            if escalate:
                samples = [
                    g.text.strip()
                    for g in self.backend.sample(
                        prompt,
                        self.config.n_samples,
                        temperature=self.config.sample_temperature,
                        options=OllamaOptions(num_predict=self.config.max_tokens),
                        system=self.config.system_prompt,
                    )
                ]
                cfeats, clusters = consistency_features(
                    generation.text.strip(),
                    samples,
                    self.backend.embed,
                    similarity_threshold=self.config.similarity_threshold,
                )
                values.update(cfeats)
                tiers_used.append(Tier.SAMPLING)
            else:
                notes.append(
                    f"tier-1 risk {cheap_risk:.2f} outside escalation band "
                    f"[{self.config.escalate_low}, {self.config.escalate_high}]; "
                    "skipped sampling"
                )

        # --- Tier 3: self-verification (opt-in) --------------------------
        if Tier.VERIFY in allowed:
            values.update(verify_features(self.backend, question, generation.text))
            tiers_used.append(Tier.VERIFY)

        fingerprint = build_fingerprint(values, allowed, cost_s=time.perf_counter() - gen_done)
        risk = self._raw_score(values, allowed)
        decision = self.policy.decide(risk)

        # A refusal is not a hallucination - it asserts nothing that could be
        # unsupported - so it gets its own decision rather than a risk score.
        #
        # This has to be handled here rather than left to the classifier.
        # Refusals are *excluded* from the training corpus (labelling "I don't
        # know" as either correct or hallucinated teaches something false), so
        # the model has never seen srf.is_refusal=1 and extrapolates arbitrarily
        # on it. Measured on llama3.2:3b, honest refusals were scoring anywhere
        # from 0.27 to 0.60 - one of them "reject" - purely on token-tier noise.
        if values.get("srf.is_refusal", 0.0) > 0:
            decision = "abstain"
            notes.append(
                "the model declined to answer; a refusal makes no factual claim, "
                "so the risk score does not apply"
            )

        return RiskReport(
            risk=risk,
            decision=decision,
            answer=generation.text.strip(),
            question=question,
            model=generation.model,
            tiers_used=tiers_used,
            fingerprint=fingerprint,
            top_factors=self._explain(fingerprint, tiers_used),
            token_risk=self._token_risk(generation),
            samples=samples,
            clusters=clusters.members if clusters else [],
            latency_s=time.perf_counter() - started,
            overhead_s=time.perf_counter() - gen_done,
            calibrated=self.model is not None,
            notes=notes,
        )

    def score_batch(self, questions: Sequence[str]) -> list[RiskReport]:
        return [self.score(q) for q in questions]

    # ----------------------------------------------------------------- internals

    def _build_prompt(self, question: str) -> str:
        return f"Question: {question}\nAnswer:"

    def _generate(self, prompt: str, answer: str | None) -> Generation:
        if answer is not None:
            # Scoring a supplied answer: Ollama cannot return logprobs for text
            # it did not generate (num_predict=0 does not suppress generation),
            # so the token tier is unavailable on this path.
            return Generation(text=answer, model=self.backend.model)
        return self.backend.generate(
            prompt,
            options=OllamaOptions(
                temperature=self.config.temperature,
                seed=self.config.seed,
                num_predict=self.config.max_tokens,
            ),
            logprobs=True,
            top_logprobs=self.config.top_logprobs,
            system=self.config.system_prompt,
        )

    def _raw_score(self, values: dict[str, float], tiers: Sequence[str]) -> float:
        """Risk in [0,1] from a trained model, or a transparent fallback."""
        if self.model is not None and self.feature_names:
            import numpy as np

            vector = np.array(
                [[float(values.get(n, 0.0)) for n in self.feature_names]], dtype=float
            )
            raw = float(self.model.predict_proba(vector)[0, 1])
            return min(max(raw, 0.0), 1.0)
        return self._heuristic(values, tiers)

    @staticmethod
    def _heuristic(values: dict[str, float], tiers: Sequence[str]) -> float:
        """Untrained fallback.

        A deliberately simple, inspectable blend of the two signals that carried
        the most weight in the pilot. It is *not* a calibrated probability and
        reports say so; it exists so the library does something sensible before
        anyone trains a model.
        """
        # mean entropy over a truncated 20-way support saturates around ln(20)
        # ~ 3.0 nats; 2.0 is a generous practical ceiling for short answers.
        entropy = values.get("tok.mean_entropy", 0.0) / 2.0
        margin_risk = 1.0 - values.get("tok.mean_margin", 1.0)

        parts = [min(entropy, 1.0), min(max(margin_risk, 0.0), 1.0)]
        weights = [0.5, 0.5]

        if Tier.SAMPLING in tiers and "cns.semantic_entropy" in values:
            # ln(K+1) is the maximum entropy when every sample differs.
            import math

            ceiling = math.log(max(values.get("cns.n_clusters", 2.0), 2.0)) or 1.0
            parts.append(min(values["cns.semantic_entropy"] / max(ceiling, 1e-6), 1.0))
            weights.append(0.6)

        # An explicit refusal is honest, not a hallucination: pull risk down.
        risk = sum(p * w for p, w in zip(parts, weights, strict=False)) / sum(weights)
        if values.get("srf.is_refusal", 0.0) > 0:
            risk *= 0.4
        return min(max(risk, 0.0), 1.0)

    def _explain(
        self,
        fingerprint: Fingerprint,
        tiers_used: Sequence[str] = (),
        k: int = 5,
    ) -> list[tuple[str, float]]:
        """Top contributing features.

        Uses the trained model's gain-based importances when available, so the
        explanation reflects the model actually doing the scoring rather than a
        hand-written story about it.
        """
        if self.model is None or not self.feature_names:
            interesting = (
                "tok.mean_entropy",
                "tok.mean_margin",
                "cns.semantic_entropy",
                "cns.top_mass",
                "srf.is_refusal",
            )
            values = fingerprint.as_dict()
            return [(n, values[n]) for n in interesting if n in values][:k]

        importances = getattr(self.model, "feature_importances_", None)
        if importances is None:
            return []
        values = fingerprint.as_dict()

        # Only explain with features that were actually computed on this request.
        # When the cascade skips sampling, the globally most-important features
        # are all cns.* sitting at 0.0, and listing those as "what drove the
        # score" is actively misleading - they drove nothing, they never ran.
        computed = {
            name
            for name, tier in zip(fingerprint.names, fingerprint.tiers, strict=False)
            if tier in tiers_used
        } if tiers_used else set(values)

        ranked = sorted(
            (
                (name, imp)
                for name, imp in zip(self.feature_names, importances, strict=False)
                if name in computed
            ),
            key=lambda kv: kv[1],
            reverse=True,
        )
        return [(name, values.get(name, 0.0)) for name, _ in ranked[:k]]

    @staticmethod
    def _token_risk(generation: Generation) -> list[tuple[str, float]]:
        """Per-token risk for the UI heat-map, normalised to [0,1]."""
        if not generation.tokens:
            return []
        has_alts = bool(generation.tokens[0].top_logprobs)
        out: list[tuple[str, float]] = []
        for t in generation.tokens:
            # Entropy where available (bounded by ln 20), else surprisal.
            value = t.entropy() / 3.0 if has_alts else min(t.surprisal / 5.0, 1.0)
            out.append((t.token, min(max(value, 0.0), 1.0)))
        return out

    # ------------------------------------------------------------ persistence

    @classmethod
    def load(
        cls,
        path: str,
        *,
        backend: OllamaBackend | None = None,
        host: str | None = None,
    ) -> HallucinationDetector:
        """Load a trained detector saved by ``halluciwatch train``."""
        from .model import load_detector

        return load_detector(path, backend=backend, host=host)

    def close(self) -> None:
        self.backend.close()

    def __enter__(self) -> HallucinationDetector:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

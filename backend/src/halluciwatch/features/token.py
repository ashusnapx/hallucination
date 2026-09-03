"""Tier-1 features: the token probability distribution of a single generation.

These are the cheapest informative signals - they come from the generation the
user already asked for. In the pilot on TriviaQA (llama3.2:1b, n=40) this family
alone reached AUROC 0.872, with ``mean_entropy`` at 0.891 on its own; adding six
extra sampled generations moved the combined score only to 0.878. That result is
why the cascade treats this tier as the default and everything else as opt-in.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from ..types import Generation, Tier, TokenLogprob
from .registry import feature

__all__ = ["TOKEN_FEATURES", "is_content_token", "token_features"]

_T = Tier.TOKEN

TOKEN_FEATURES = [
    feature("tok.mean_entropy", _T, "Mean truncated-support entropy over generated tokens."),
    feature("tok.max_entropy", _T, "Peak per-token entropy - the single most uncertain step."),
    feature("tok.std_entropy", _T, "Spread of per-token entropy."),
    feature("tok.p90_entropy", _T, "90th-percentile entropy; robust version of the max."),
    feature("tok.mean_surprisal", _T, "Mean negative log-prob of the chosen tokens (nats)."),
    feature("tok.max_surprisal", _T, "Largest single-token surprisal."),
    feature("tok.perplexity", _T, "exp(mean surprisal) - sequence perplexity."),
    feature("tok.varentropy", _T, "Variance of surprisal; spiky uncertainty rather than uniform."),
    feature(
        "tok.mean_margin", _T,
        "Mean p(top1)-p(top2). Low margin = the model nearly chose something else.",
        higher_is_riskier=False,
    ),
    feature(
        "tok.min_margin", _T,
        "Smallest top1-top2 gap across the answer.",
        higher_is_riskier=False,
    ),
    feature(
        "tok.mean_top1", _T, "Mean probability of the chosen token.", higher_is_riskier=False,
    ),
    feature(
        "tok.min_top1", _T,
        "Lowest top-1 probability - the weakest link in the answer.",
        higher_is_riskier=False,
    ),
    feature("tok.frac_low_conf", _T, "Fraction of tokens with top-1 probability below 0.5."),
    feature("tok.max_low_conf_run", _T, "Longest consecutive run of low-confidence tokens."),
    feature(
        "tok.mean_content_entropy", _T,
        "Mean entropy restricted to content tokens, ignoring function words and "
        "punctuation whose uncertainty is stylistic rather than factual.",
    ),
    feature(
        "tok.max_content_entropy", _T, "Peak entropy among content tokens only.",
    ),
    feature(
        "tok.entropy_slope", _T,
        "Least-squares slope of entropy across token position; positive means the "
        "model grows less certain as it commits to detail.",
    ),
    feature(
        "tok.first_token_entropy", _T,
        "Entropy at the first generated token, where the answer is chosen.",
    ),
    feature("tok.n_tokens", _T, "Length of the generation in tokens.", higher_is_riskier=False),
]

# Function words and punctuation carry uncertainty that is stylistic rather than
# factual ("the" vs "a"). Restricting entropy to content tokens is the same idea
# as Shifting-Attention-to-Relevance / claim-conditioned probability.
_STOPWORDS = frozenset(
    """
    a an the of in on at to for from by with and or but if then than that this these those
    is are was were be been being am do does did doing have has had having will would shall
    should can could may might must it its as not no nor so such there here what which who
    whom whose when where why how all any both each few more most other some only own same
    very s t just don now i you he she they we me him her them my your his their our
    """.split()
)


def is_content_token(token: str) -> bool:
    """True when a token carries factual content rather than syntax."""
    stripped = token.strip()
    if not stripped:
        return False
    if not any(ch.isalnum() for ch in stripped):
        return False
    return stripped.lower().strip("'\".,;:!?()[]{}") not in _STOPWORDS


def _slope(values: Sequence[float]) -> float:
    """Least-squares slope of ``values`` against their index."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    denom = sum((i - mean_x) ** 2 for i in range(n))
    if denom <= 0:
        return 0.0
    num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    return num / denom


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = math.floor(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _longest_run(flags: Sequence[bool]) -> int:
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def token_features(generation: Generation, low_conf_threshold: float = 0.5) -> dict[str, float]:
    """Compute tier-1 features from one generation.

    Degrades gracefully: with ``top_logprobs=0`` only surprisal-based features
    are meaningful, and the distribution-based ones (entropy, margin) return 0.
    """
    tokens: list[TokenLogprob] = list(generation.tokens)
    if not tokens:
        return {name: 0.0 for name in TOKEN_FEATURES}

    surprisals = [t.surprisal for t in tokens]
    has_alts = bool(tokens[0].top_logprobs)

    entropies = [t.entropy() for t in tokens] if has_alts else [0.0] * len(tokens)
    margins = [t.margin() for t in tokens] if has_alts else [0.0] * len(tokens)
    top1 = [t.top_probability() for t in tokens] if has_alts else [t.probability for t in tokens]

    content_idx = [i for i, t in enumerate(tokens) if is_content_token(t.token)]
    content_entropy = [entropies[i] for i in content_idx] or entropies

    low_conf = [p < low_conf_threshold for p in top1]
    mean_surprisal = statistics.fmean(surprisals)

    return {
        "tok.mean_entropy": statistics.fmean(entropies),
        "tok.max_entropy": max(entropies),
        "tok.std_entropy": statistics.pstdev(entropies) if len(entropies) > 1 else 0.0,
        "tok.p90_entropy": _percentile(entropies, 0.90),
        "tok.mean_surprisal": mean_surprisal,
        "tok.max_surprisal": max(surprisals),
        # Clamped so a single pathological token cannot produce inf and poison
        # the tree splits downstream.
        "tok.perplexity": math.exp(min(mean_surprisal, 20.0)),
        "tok.varentropy": statistics.pvariance(surprisals) if len(surprisals) > 1 else 0.0,
        "tok.mean_margin": statistics.fmean(margins),
        "tok.min_margin": min(margins),
        "tok.mean_top1": statistics.fmean(top1),
        "tok.min_top1": min(top1),
        "tok.frac_low_conf": sum(low_conf) / len(low_conf),
        "tok.max_low_conf_run": float(_longest_run(low_conf)),
        "tok.mean_content_entropy": statistics.fmean(content_entropy),
        "tok.max_content_entropy": max(content_entropy),
        "tok.entropy_slope": _slope(entropies),
        "tok.first_token_entropy": entropies[0],
        "tok.n_tokens": float(len(tokens)),
    }

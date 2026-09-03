"""Tier-2 features: self-consistency across independently sampled answers.

This is the semantic-entropy / SelfCheckGPT family. It is by far the most
expensive tier - K extra generations - and the pilot found it adds little on
short-form QA with a small model (tier-1 alone 0.872 AUROC vs 0.878 with six
extra samples). It earns its cost on longer answers and on questions where the
greedy decode is *confidently* wrong, which is precisely the case cheap
token-level signals miss: in the pilot, "who was the 14th person to walk on the
Moon?" produced a confident "Neil Armstrong" whose token entropy looked benign,
while the sampled answers split into four clusters including two invented names.

The cascade therefore spends this tier only inside the uncertainty band.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Sequence

from ..cluster import ClusterResult, cluster_answers, normalise_answer
from ..types import Tier
from .registry import feature

__all__ = ["CONSISTENCY_FEATURES", "consistency_features"]

_C = Tier.SAMPLING

CONSISTENCY_FEATURES = [
    feature(
        "cns.semantic_entropy", _C,
        "Entropy over meaning-clusters of sampled answers (Farquhar et al. 2024). "
        "High when the model tells a different story each time.",
    ),
    feature(
        "cns.n_clusters", _C, "Number of distinct meanings among the samples.",
    ),
    feature(
        "cns.top_mass", _C,
        "Share of samples agreeing with the majority meaning.",
        higher_is_riskier=False,
    ),
    feature(
        "cns.answer_in_majority", _C,
        "Whether the returned answer belongs to the largest cluster.",
        higher_is_riskier=False,
    ),
    feature(
        "cns.exact_agreement", _C,
        "Fraction of samples exactly matching the returned answer after normalisation.",
        higher_is_riskier=False,
    ),
    feature(
        "cns.mean_similarity", _C,
        "Mean pairwise embedding similarity between the answer and each sample.",
        higher_is_riskier=False,
    ),
    feature(
        "cns.min_similarity", _C,
        "Similarity to the most divergent sample.",
        higher_is_riskier=False,
    ),
    feature(
        "cns.length_dispersion", _C,
        "Coefficient of variation of sample lengths; unstable length signals an "
        "unstable answer.",
    ),
    feature(
        "cns.refusal_rate", _C,
        "Fraction of samples that refused. A model that sometimes refuses and "
        "sometimes answers is guessing.",
    ),
]


def consistency_features(
    answer: str,
    samples: Sequence[str],
    embed_fn: Callable[[Sequence[str]], list[list[float]]] | None = None,
    *,
    similarity_threshold: float = 0.92,
    entail_fn: Callable[[str, str], bool] | None = None,
) -> tuple[dict[str, float], ClusterResult | None]:
    """Compute tier-2 features and return the clustering for display.

    The returned answer is clustered *together with* the samples so that
    ``answer_in_majority`` is well defined.
    """
    from .surface import looks_like_refusal

    if not samples:
        return {name: 0.0 for name in CONSISTENCY_FEATURES}, None

    pool = [answer, *samples]
    result = cluster_answers(
        pool,
        embed_fn,
        similarity_threshold=similarity_threshold,
        entail_fn=entail_fn,
    )

    # Index 0 is the returned answer; find which cluster it landed in.
    answer_cluster = next((g for g in result.clusters if 0 in g), [0])
    largest = max(result.clusters, key=len) if result.clusters else []
    in_majority = float(answer_cluster is largest or len(answer_cluster) == len(largest))

    norm_answer = normalise_answer(answer)
    exact = sum(1 for s in samples if normalise_answer(s) == norm_answer) / len(samples)

    mean_sim = min_sim = 0.0
    if embed_fn is not None:
        try:
            vectors = embed_fn(pool)
            from ..backends.ollama import cosine

            sims = [cosine(vectors[0], v) for v in vectors[1:]]
            if sims:
                mean_sim, min_sim = statistics.fmean(sims), min(sims)
        except Exception:
            mean_sim = min_sim = 0.0

    lengths = [len(s.split()) for s in samples]
    mean_len = statistics.fmean(lengths) if lengths else 0.0
    dispersion = (
        statistics.pstdev(lengths) / mean_len if len(lengths) > 1 and mean_len > 0 else 0.0
    )

    feats = {
        "cns.semantic_entropy": result.entropy,
        "cns.n_clusters": float(result.n_clusters),
        "cns.top_mass": result.top_mass,
        "cns.answer_in_majority": in_majority,
        "cns.exact_agreement": exact,
        "cns.mean_similarity": mean_sim,
        "cns.min_similarity": min_sim,
        "cns.length_dispersion": dispersion,
        "cns.refusal_rate": sum(looks_like_refusal(s) for s in samples) / len(samples),
    }
    return feats, result

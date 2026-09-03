"""Feature extraction: the hallucination fingerprint.

Four tiers, ordered by cost. See each module's docstring for what it measures
and what it actually bought on the reference benchmark.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..types import Fingerprint, Tier
from .consistency import CONSISTENCY_FEATURES, consistency_features
from .registry import REGISTRY, FeatureRegistry, FeatureSpec
from .surface import SURFACE_FEATURES, looks_like_refusal, surface_features
from .token import TOKEN_FEATURES, is_content_token, token_features
from .verify import VERIFY_FEATURES, p_true, verify_features

__all__ = [
    "CONSISTENCY_FEATURES",
    "REGISTRY",
    "SURFACE_FEATURES",
    "TOKEN_FEATURES",
    "VERIFY_FEATURES",
    "FeatureRegistry",
    "FeatureSpec",
    "Tier",
    "build_fingerprint",
    "consistency_features",
    "feature_names",
    "is_content_token",
    "looks_like_refusal",
    "p_true",
    "surface_features",
    "token_features",
    "verify_features",
]


def feature_names(tiers: Sequence[str] | None = None) -> list[str]:
    """Ordered feature names for the given tiers (all tiers by default)."""
    return REGISTRY.names(tiers)


def build_fingerprint(
    values: dict[str, float],
    tiers: Sequence[str] | None = None,
    *,
    cost_s: float = 0.0,
) -> Fingerprint:
    """Assemble a dense, ordered fingerprint from a sparse feature dict.

    Features belonging to a requested tier that were not computed are filled
    with 0.0 rather than dropped, so the vector length is a function of the
    requested tiers alone. That keeps a model trained on tiers ``{surface,
    token}`` scoreable even when a caller happens to supply extra features.
    """
    names = REGISTRY.names(tiers)
    ordered = [float(values.get(name, 0.0)) for name in names]
    return Fingerprint(
        names=names,
        values=ordered,
        tiers=REGISTRY.tiers_for(names),
        cost_s=cost_s,
    )

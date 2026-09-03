"""Feature registry.

Every feature is declared once, with its name, tier and a docstring explaining
what it measures and why it should correlate with hallucination. The registry
guarantees a **stable, ordered** feature vector: models are trained and scored
against the same names in the same positions, and a mismatch is an error rather
than a silent misalignment.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

__all__ = ["REGISTRY", "FeatureRegistry", "FeatureSpec", "feature"]


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    name: str
    tier: str
    description: str
    higher_is_riskier: bool
    """Expected sign. Used only for reporting/sanity checks, never for scoring."""


class FeatureRegistry:
    """An ordered collection of feature specs, grouped by tier."""

    def __init__(self) -> None:
        self._specs: list[FeatureSpec] = []
        self._seen: set[str] = set()

    def add(self, spec: FeatureSpec) -> None:
        if spec.name in self._seen:
            raise ValueError(f"duplicate feature name: {spec.name}")
        self._seen.add(spec.name)
        self._specs.append(spec)

    def register(
        self,
        name: str,
        tier: str,
        description: str,
        *,
        higher_is_riskier: bool = True,
    ) -> None:
        self.add(FeatureSpec(name, tier, description, higher_is_riskier))

    def names(self, tiers: Iterable[str] | None = None) -> list[str]:
        allowed = set(tiers) if tiers is not None else None
        return [s.name for s in self._specs if allowed is None or s.tier in allowed]

    def tiers_for(self, names: Iterable[str]) -> list[str]:
        lookup = {s.name: s.tier for s in self._specs}
        return [lookup.get(n, "unknown") for n in names]

    def specs(self, tiers: Iterable[str] | None = None) -> list[FeatureSpec]:
        allowed = set(tiers) if tiers is not None else None
        return [s for s in self._specs if allowed is None or s.tier in allowed]

    def describe(self, name: str) -> str:
        for s in self._specs:
            if s.name == name:
                return s.description
        return ""

    def __len__(self) -> int:
        return len(self._specs)


REGISTRY = FeatureRegistry()


def feature(name: str, tier: str, description: str, *, higher_is_riskier: bool = True) -> str:
    """Declare a feature in the global registry and return its name."""
    REGISTRY.register(name, tier, description, higher_is_riskier=higher_is_riskier)
    return name

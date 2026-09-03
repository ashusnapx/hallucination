"""Signal-family ablation: what does each tier actually buy?

The premise of the cascade is that expensive signals are not uniformly worth
their cost. That is a claim about *your* model and *your* data, not a universal
truth, so it has to be measured rather than assumed. This module trains a
detector on each tier subset and reports AUROC against the marginal cost in
seconds per query.

The pilot that motivated the design (llama3.2:1b, 40 TriviaQA questions)::

    tier-1 token signals only            AUROC 0.872   +0.09s/query
    + 6 sampled generations (tier 2)     AUROC 0.878   +6 generations
    + P(True) self-verification          AUROC 0.841   +1 generation

Sampling bought 0.006 AUROC for roughly six times the compute, and
self-verification was actively harmful. Run this on your own corpus before
trusting either result - both are model- and dataset-dependent, and the numbers
above come from a deliberately small pilot.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..features import REGISTRY
from ..types import Tier

__all__ = ["AblationRow", "format_ablation", "run_ablation"]

# Measured marginal cost per query on the reference machine (Apple M1,
# llama3.2:1b, 60 generated tokens). SAMPLING scales with n_samples.
_TIER_COST_S = {
    Tier.SURFACE: 0.0,
    Tier.TOKEN: 1.38,      # top_logprobs penalty: 1.71s -> 3.09s
    Tier.SAMPLING: 1.71,   # per sample
    Tier.VERIFY: 0.35,     # one 1-token generation
}


@dataclass
class AblationRow:
    tiers: tuple[str, ...]
    auroc: float
    auprc: float
    aurc: float
    n_features: int
    cost_s: float
    auroc_ci: tuple[float, float] = (0.0, 0.0)

    @property
    def label(self) -> str:
        return "+".join(t[:4] for t in self.tiers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tiers": list(self.tiers),
            "auroc": round(self.auroc, 4),
            "auroc_ci95": [round(self.auroc_ci[0], 4), round(self.auroc_ci[1], 4)],
            "auprc": round(self.auprc, 4),
            "aurc": round(self.aurc, 4),
            "n_features": self.n_features,
            "cost_s": round(self.cost_s, 3),
        }


def _tier_cost(tiers: Sequence[str], n_samples: int) -> float:
    total = 0.0
    for tier in tiers:
        unit = _TIER_COST_S.get(tier, 0.0)
        total += unit * n_samples if tier == Tier.SAMPLING else unit
    return total


def run_ablation(
    rows: Sequence[dict[str, Any]],
    *,
    tiers: Sequence[str] = (Tier.SURFACE, Tier.TOKEN, Tier.SAMPLING),
    kind: str = "xgboost",
    seed: int = 42,
    n_splits: int = 5,
    n_samples: int = 6,
    include_singletons: bool = True,
) -> list[AblationRow]:
    """Evaluate every cumulative (and optionally singleton) tier combination."""
    from ..data.build import corpus_to_matrix
    from ..model import _grouped_folds
    from .metrics import bootstrap_auroc_ci

    combos: list[tuple[str, ...]] = []
    if include_singletons:
        combos.extend((t,) for t in tiers)
    for size in range(2, len(tiers) + 1):
        combos.append(tuple(tiers[:size]))
    # de-duplicate, preserving order
    seen: set[tuple[str, ...]] = set()
    combos = [c for c in combos if not (c in seen or seen.add(c))]

    results: list[AblationRow] = []
    for combo in combos:
        names = REGISTRY.names(combo)
        if not names:
            continue
        X, y, groups, _ = corpus_to_matrix(rows, names)
        if len(y) == 0 or len(np.unique(y)) < 2:
            continue
        folds = _grouped_folds(groups, n_splits, seed)

        oof = np.zeros(len(y), dtype=float)
        from ..model import _make_estimator

        for train_idx, test_idx in folds:
            est = _make_estimator(
                kind, seed, int(y[train_idx].sum()), int((1 - y[train_idx]).sum())
            )
            est.fit(X[train_idx], y[train_idx])
            oof[test_idx] = est.predict_proba(X[test_idx])[:, 1]

        from sklearn.metrics import average_precision_score, roc_auc_score

        order = np.argsort(oof)
        aurc = float((np.cumsum(y[order]) / np.arange(1, len(y) + 1)).mean())

        results.append(
            AblationRow(
                tiers=combo,
                auroc=float(roc_auc_score(y, oof)),
                auprc=float(average_precision_score(y, oof)),
                aurc=aurc,
                n_features=len(names),
                cost_s=_tier_cost(combo, n_samples),
                auroc_ci=bootstrap_auroc_ci(oof, y, 500, seed),
            )
        )
    return results


def single_feature_auroc(
    rows: Sequence[dict[str, Any]], top_k: int = 15
) -> list[tuple[str, float]]:
    """AUROC of each individual feature, direction-corrected.

    A strong single feature is a reason to question whether the model is adding
    anything: in the pilot ``tok.mean_entropy`` alone scored 0.891 while the
    full model reached 0.878.
    """
    from sklearn.metrics import roc_auc_score

    from ..data.build import corpus_to_matrix

    names = REGISTRY.names()
    X, y, _, _ = corpus_to_matrix(rows, names)
    if len(y) == 0 or len(np.unique(y)) < 2:
        return []

    scored: list[tuple[str, float]] = []
    for i, name in enumerate(names):
        column = X[:, i]
        if np.all(column == column[0]):
            continue
        auroc = roc_auc_score(y, column)
        scored.append((name, max(auroc, 1.0 - auroc)))
    return sorted(scored, key=lambda kv: kv[1], reverse=True)[:top_k]


def format_ablation(results: Sequence[AblationRow], baseline_auroc: float | None = None) -> str:
    """Render the ablation as a text table with cost-effectiveness."""
    if not results:
        return "no ablation results (corpus too small or single-class)"

    lines = [
        f"{'tiers':<28} {'feats':>5} {'AUROC':>7} {'95% CI':>15} "
        f"{'AUPRC':>7} {'cost/q':>8} {'ΔAUROC/s':>9}",
        "-" * 88,
    ]
    cheapest = min(results, key=lambda r: r.cost_s)
    for row in sorted(results, key=lambda r: r.cost_s):
        delta = row.auroc - cheapest.auroc
        extra_cost = row.cost_s - cheapest.cost_s
        efficiency = delta / extra_cost if extra_cost > 0.01 else float("nan")
        eff = "  baseline" if row is cheapest else f"{efficiency:>9.4f}"
        lines.append(
            f"{'+'.join(row.tiers):<28} {row.n_features:>5} {row.auroc:>7.3f} "
            f"[{row.auroc_ci[0]:.3f},{row.auroc_ci[1]:.3f}] {row.auprc:>7.3f} "
            f"{row.cost_s:>7.2f}s {eff}"
        )
    return "\n".join(lines)

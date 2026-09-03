"""Metrics for a hallucination detector.

AUROC is the headline number in this literature, but on its own it is a
misleading way to describe a detector that is supposed to *make decisions*:

* It is invariant to any monotone rescaling, so a badly calibrated model and a
  well calibrated one score identically. ECE and Brier catch that.
* It weights both classes equally regardless of prevalence. AUPRC is the more
  honest summary when hallucinations are rare.
* It says nothing about behaviour at the operating point that matters. The
  risk-coverage curve does: it answers "if I auto-accept the safest X% of
  answers, what error rate do I inherit?"

``evaluate`` reports all of them together.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ..calibration import brier_score, expected_calibration_error

__all__ = ["DetectorMetrics", "bootstrap_auroc_ci", "evaluate", "risk_coverage_curve"]


@dataclass
class DetectorMetrics:
    auroc: float
    auprc: float
    f1: float
    precision: float
    recall: float
    brier: float
    ece: float
    aurc: float
    base_rate: float
    n: int
    threshold: float = 0.5
    auroc_ci: tuple[float, float] = (0.0, 0.0)
    coverage_at_10pct_error: float = 0.0

    def to_dict(self) -> dict[str, float | int | tuple[float, float]]:
        return {
            "n": self.n,
            "base_rate": round(self.base_rate, 4),
            "auroc": round(self.auroc, 4),
            "auroc_ci95": (round(self.auroc_ci[0], 4), round(self.auroc_ci[1], 4)),
            "auprc": round(self.auprc, 4),
            "f1": round(self.f1, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "brier": round(self.brier, 4),
            "ece": round(self.ece, 4),
            "aurc": round(self.aurc, 4),
            "coverage_at_10pct_error": round(self.coverage_at_10pct_error, 4),
            "threshold": self.threshold,
        }

    def summary(self) -> str:
        lo, hi = self.auroc_ci
        return (
            f"AUROC {self.auroc:.3f} [{lo:.3f}-{hi:.3f}]  "
            f"AUPRC {self.auprc:.3f}  F1 {self.f1:.3f}  "
            f"ECE {self.ece:.3f}  Brier {self.brier:.3f}  "
            f"coverage@10%err {self.coverage_at_10pct_error:.0%}  (n={self.n})"
        )


def evaluate(
    risks: Sequence[float],
    labels: Sequence[int],
    *,
    threshold: float = 0.5,
    bootstrap: int = 1000,
    seed: int = 42,
) -> DetectorMetrics:
    """Compute the full metric set. ``labels``: 1 = hallucinated."""
    from sklearn.metrics import (
        average_precision_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    p = np.asarray(risks, dtype=float)
    y = np.asarray(labels, dtype=int)
    if len(p) == 0:
        return DetectorMetrics(*([0.0] * 9), n=0)

    single_class = len(np.unique(y)) < 2
    pred = (p >= threshold).astype(int)

    auroc = 0.5 if single_class else float(roc_auc_score(y, p))
    auprc = float(y.mean()) if single_class else float(average_precision_score(y, p))

    return DetectorMetrics(
        auroc=auroc,
        auprc=auprc,
        f1=float(f1_score(y, pred, zero_division=0)),
        precision=float(precision_score(y, pred, zero_division=0)),
        recall=float(recall_score(y, pred, zero_division=0)),
        brier=brier_score(p, y),
        ece=expected_calibration_error(p, y),
        aurc=_aurc(p, y),
        base_rate=float(y.mean()),
        n=len(y),
        threshold=threshold,
        auroc_ci=(0.0, 0.0) if single_class else bootstrap_auroc_ci(p, y, bootstrap, seed),
        coverage_at_10pct_error=coverage_at_error(p, y, 0.10),
    )


def _aurc(risks: np.ndarray, labels: np.ndarray) -> float:
    order = np.argsort(risks)
    errors = np.cumsum(labels[order]) / np.arange(1, len(labels) + 1)
    return float(errors.mean())


def risk_coverage_curve(
    risks: Sequence[float], labels: Sequence[int]
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(coverage, error_rate)``.

    Point *i* answers: if we auto-accept the ``coverage[i]`` fraction of answers
    the detector considers safest, ``error_rate[i]`` of them are wrong. This is
    the curve to show a stakeholder - it converts a ranking into an operating
    decision.
    """
    p = np.asarray(risks, dtype=float)
    y = np.asarray(labels, dtype=int)
    if len(p) == 0:
        return np.array([]), np.array([])
    order = np.argsort(p)
    errors = np.cumsum(y[order]) / np.arange(1, len(y) + 1)
    coverage = np.arange(1, len(y) + 1) / len(y)
    return coverage, errors


def coverage_at_error(
    risks: Sequence[float], labels: Sequence[int], target_error: float
) -> float:
    """Largest fraction auto-acceptable while keeping error at/below target."""
    coverage, errors = risk_coverage_curve(risks, labels)
    if len(coverage) == 0:
        return 0.0
    ok = np.where(errors <= target_error)[0]
    return float(coverage[ok[-1]]) if len(ok) else 0.0


def bootstrap_auroc_ci(
    risks: Sequence[float], labels: Sequence[int], n_boot: int = 1000, seed: int = 42
) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for AUROC.

    Included because these corpora are small - a few hundred rows - and a point
    estimate of 0.87 from n=200 deserves an interval next to it rather than a
    claim of three-decimal precision.
    """
    from sklearn.metrics import roc_auc_score

    p = np.asarray(risks, dtype=float)
    y = np.asarray(labels, dtype=int)
    if len(p) < 10 or len(np.unique(y)) < 2:
        return (0.0, 0.0)

    rng = np.random.default_rng(seed)
    scores: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        scores.append(roc_auc_score(y[idx], p[idx]))
    if not scores:
        return (0.0, 0.0)
    return (
        float(np.percentile(scores, 2.5)),
        float(np.percentile(scores, 97.5)),
    )

"""Evaluation: metrics, confidence intervals, and signal-family ablation."""

from __future__ import annotations

from .ablation import AblationRow, format_ablation, run_ablation, single_feature_auroc
from .metrics import (
    DetectorMetrics,
    bootstrap_auroc_ci,
    coverage_at_error,
    evaluate,
    risk_coverage_curve,
)

__all__ = [
    "AblationRow",
    "DetectorMetrics",
    "bootstrap_auroc_ci",
    "coverage_at_error",
    "evaluate",
    "format_ablation",
    "risk_coverage_curve",
    "run_ablation",
    "single_feature_auroc",
]

"""Turning a classifier score into a decision you can defend.

A raw gradient-boosting score is not a probability, and thresholding it at 0.5
is arbitrary. Two layers fix that:

* **Calibration** (isotonic regression) maps scores to probabilities that mean
  what they say - among answers scored 0.30, about 30% really are wrong.
  Measured by expected calibration error and Brier score, not AUROC, which is
  invariant to any monotone rescaling and therefore blind to calibration.
* **Conformal thresholds** pick the accept/reject cut-offs from a held-out
  calibration set so that the error rate among *accepted* answers is bounded at
  a target level, with the bound holding under exchangeability rather than by
  assumption.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise

import numpy as np

__all__ = [
    "Calibrator",
    "DecisionPolicy",
    "brier_score",
    "expected_calibration_error",
]


@dataclass
class Calibrator:
    """Isotonic calibration of raw classifier scores into probabilities.

    Isotonic rather than Platt scaling: it is non-parametric, so it can correct
    the S-shaped miscalibration typical of boosted trees without assuming a
    logistic link. It needs a few hundred calibration points to behave; below
    that it will happily overfit, so ``fit`` refuses and falls back to identity.
    """

    min_samples: int = 100
    _iso: object | None = field(default=None, repr=False)
    fitted: bool = False

    def fit(self, scores: Sequence[float], labels: Sequence[int]) -> Calibrator:
        from sklearn.isotonic import IsotonicRegression

        s = np.asarray(scores, dtype=float)
        y = np.asarray(labels, dtype=int)
        if len(s) < self.min_samples or len(np.unique(y)) < 2:
            self.fitted = False
            return self
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        iso.fit(s, y)
        self._iso = iso
        self.fitted = True
        return self

    def transform(self, scores: Sequence[float]) -> np.ndarray:
        s = np.asarray(scores, dtype=float)
        if not self.fitted or self._iso is None:
            return s
        return np.clip(self._iso.predict(s), 0.0, 1.0)  # type: ignore[attr-defined]


@dataclass
class DecisionPolicy:
    """Maps a calibrated risk into ``accept`` / ``review`` / ``reject``.

    Thresholds are learned from a calibration set rather than hard-coded:

    * ``accept_below`` is the largest risk at which the observed error rate
      among accepted answers still satisfies ``target_error``. This is the
      conformal part - it is a quantile of the calibration distribution, so the
      guarantee is empirical rather than assumed.
    * ``reject_above`` is set at a high-precision point so that flagged answers
      are worth a human's attention.

    ``coverage`` records what fraction of the calibration set was auto-accepted,
    which is the number that actually matters operationally: a detector that
    guarantees low error by abstaining on everything is useless.
    """

    accept_below: float = 0.30
    reject_above: float = 0.70
    target_error: float = 0.10
    coverage: float = 0.0
    achieved_error: float = 0.0
    fitted: bool = False

    def fit(
        self,
        risks: Sequence[float],
        labels: Sequence[int],
        *,
        target_error: float | None = None,
        min_precision: float = 0.75,
    ) -> DecisionPolicy:
        r = np.asarray(risks, dtype=float)
        y = np.asarray(labels, dtype=int)
        if len(r) == 0 or len(np.unique(y)) < 2:
            return self

        if target_error is not None:
            self.target_error = target_error

        order = np.argsort(r)
        r_sorted, y_sorted = r[order], y[order]
        # Error rate among the k lowest-risk answers, for every k.
        cum_err = np.cumsum(y_sorted) / np.arange(1, len(y_sorted) + 1)

        ok = np.where(cum_err <= self.target_error)[0]
        if len(ok):
            k = int(ok[-1])
            self.accept_below = float(r_sorted[k])
            self.coverage = (k + 1) / len(r_sorted)
            self.achieved_error = float(cum_err[k])
        else:
            # Cannot hit the target at any coverage; accept nothing automatically.
            self.accept_below = float(r_sorted[0])
            self.coverage = 0.0
            self.achieved_error = float(cum_err[0])

        # Reject threshold: lowest risk at which precision for "is wrong" clears
        # min_precision, so flagged items are mostly genuinely wrong.
        desc = np.argsort(-r)
        y_desc = y[desc]
        r_desc = r[desc]
        prec = np.cumsum(y_desc) / np.arange(1, len(y_desc) + 1)
        good = np.where(prec >= min_precision)[0]
        self.reject_above = float(r_desc[int(good[-1])]) if len(good) else 1.0

        if self.reject_above < self.accept_below:
            self.reject_above = self.accept_below
        self.fitted = True
        return self

    def decide(self, risk: float) -> str:
        if risk <= self.accept_below:
            return "accept"
        if risk >= self.reject_above:
            return "reject"
        return "review"

    def to_dict(self) -> dict[str, float | bool]:
        return {
            "accept_below": round(self.accept_below, 4),
            "reject_above": round(self.reject_above, 4),
            "target_error": self.target_error,
            "coverage": round(self.coverage, 4),
            "achieved_error": round(self.achieved_error, 4),
            "fitted": self.fitted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DecisionPolicy:
        return cls(
            accept_below=float(data.get("accept_below", 0.30)),
            reject_above=float(data.get("reject_above", 0.70)),
            target_error=float(data.get("target_error", 0.10)),
            coverage=float(data.get("coverage", 0.0)),
            achieved_error=float(data.get("achieved_error", 0.0)),
            fitted=bool(data.get("fitted", False)),
        )


def expected_calibration_error(
    probs: Sequence[float], labels: Sequence[int], n_bins: int = 10
) -> float:
    """ECE with equal-width bins: mean |confidence - accuracy| over bins."""
    p = np.asarray(probs, dtype=float)
    y = np.asarray(labels, dtype=int)
    if len(p) == 0:
        return 0.0
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    total = 0.0
    for lo, hi in pairwise(edges):
        mask = (p > lo) & (p <= hi) if lo > 0 else (p >= lo) & (p <= hi)
        if not mask.any():
            continue
        total += mask.mean() * abs(p[mask].mean() - y[mask].mean())
    return float(total)


def brier_score(probs: Sequence[float], labels: Sequence[int]) -> float:
    """Mean squared error between predicted probability and outcome."""
    p = np.asarray(probs, dtype=float)
    y = np.asarray(labels, dtype=float)
    if len(p) == 0:
        return 0.0
    return float(np.mean((p - y) ** 2))

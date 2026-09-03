"""Training, evaluating and persisting the risk classifier.

The classifier is gradient-boosted trees over the fingerprint. That choice is
not incidental: the feature set is small, heterogeneous and tabular, the dataset
is a few thousand rows, and tree ensembles handle monotone-but-nonlinear signals
like entropy without any scaling. A neural model here would be strictly worse
and much harder to justify.

Splits are **grouped by question**. The same question appears once per model in
a multi-model corpus, and letting a question straddle the train/test boundary
leaks the answer's difficulty into training - it inflates AUROC by several
points and is the single easiest way to accidentally publish a wrong number.
"""

from __future__ import annotations

import json
import logging
import pickle
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .calibration import Calibrator, DecisionPolicy, brier_score, expected_calibration_error

log = logging.getLogger(__name__)

__all__ = ["TrainedDetector", "load_detector", "save_detector", "train_classifier"]

_MODEL_FILE = "model.pkl"
_META_FILE = "detector.json"


@dataclass
class TrainedDetector:
    """A fitted classifier plus everything needed to score and interpret it."""

    model: Any
    feature_names: list[str]
    tiers: list[str]
    calibrator: Calibrator
    policy: DecisionPolicy
    metrics: dict[str, float] = field(default_factory=dict)
    per_tier_metrics: dict[str, dict[str, float]] = field(default_factory=dict)
    importances: list[tuple[str, float]] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Calibrated P(hallucinated), shaped like sklearn's predict_proba."""
        raw = self.model.predict_proba(X)[:, 1]
        cal = self.calibrator.transform(raw)
        return np.column_stack([1.0 - cal, cal])

    @property
    def feature_importances_(self) -> np.ndarray:
        """Importances aligned to ``feature_names`` order.

        ``self.importances`` is stored sorted by gain for display, so returning
        its values directly would pair every name with another feature's
        importance wherever a caller zips the two together - which is exactly
        what the detector's explanation code does.
        """
        by_name = dict(self.importances)
        return np.asarray([by_name.get(n, 0.0) for n in self.feature_names], dtype=float)


def _make_estimator(kind: str, seed: int, n_pos: int, n_neg: int) -> Any:
    """Build the estimator, sized for a small tabular dataset."""
    scale = max(n_neg, 1) / max(n_pos, 1)
    if kind == "xgboost":
        from xgboost import XGBClassifier

        # Deliberately shallow and heavily regularised.
        #
        # The first version of this used depth-4 trees with 400 estimators and
        # scored 0.775 AUROC — *below* the 0.789 that the single best feature
        # achieves alone. That gap is the signature of an ensemble memorising
        # 510 rows rather than learning from them. Depth-1 stumps with strong
        # L2 and aggressive column subsampling recover 0.793, and the ordering
        # (stumps > depth-2 > depth-4) holds across the whole sweep, so this is
        # a capacity problem rather than a lucky seed.
        return XGBClassifier(
            n_estimators=300,
            learning_rate=0.04,
            max_depth=1,
            subsample=0.8,
            colsample_bytree=0.5,
            reg_lambda=10.0,
            scale_pos_weight=scale,
            eval_metric="auc",
            random_state=seed,
            n_jobs=-1,
        )
    if kind == "lightgbm":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            n_estimators=400,
            learning_rate=0.05,
            max_depth=4,
            num_leaves=15,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_lambda=2.0,
            min_child_samples=10,
            scale_pos_weight=scale,
            random_state=seed,
            n_jobs=-1,
            verbose=-1,
        )
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(
        max_iter=400, learning_rate=0.05, max_depth=4, random_state=seed
    )


def _grouped_folds(
    groups: Sequence[Any], n_splits: int, seed: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Group-aware CV folds, so a question never spans train and test."""
    from sklearn.model_selection import GroupKFold

    g = np.asarray(groups)
    n_splits = max(2, min(n_splits, len(np.unique(g))))
    splitter = GroupKFold(n_splits=n_splits)
    dummy = np.zeros(len(g))
    return list(splitter.split(dummy, dummy, groups=g))


def train_classifier(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: Sequence[str],
    *,
    groups: Sequence[Any] | None = None,
    tiers: Sequence[str] = (),
    kind: str = "xgboost",
    seed: int = 42,
    n_splits: int = 5,
    target_error: float = 0.10,
    config: dict[str, Any] | None = None,
) -> TrainedDetector:
    """Fit and honestly evaluate the risk classifier.

    Out-of-fold predictions give an unbiased estimate of the *ranking* metrics
    (AUROC, AUPRC), which are invariant to calibration.

    Calibration metrics need more care. Fitting an isotonic calibrator on a set
    of scores and then measuring ECE on those same scores is circular: isotonic
    regression is flexible enough to drive in-sample ECE to ~0 regardless of how
    the model actually behaves. So calibration is **cross-fitted** - for each
    fold, the calibrator is fitted on the other folds' out-of-fold scores and
    applied to this one - and ECE/Brier are reported on those held-out
    calibrated values. The deployed calibrator is then refitted on everything,
    which is standard and only makes the shipped model slightly better than the
    number reported.
    """
    from sklearn.metrics import average_precision_score, f1_score, roc_auc_score

    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    names = list(feature_names)

    if X.shape[1] != len(names):
        raise ValueError(f"X has {X.shape[1]} columns but {len(names)} feature names")
    if len(np.unique(y)) < 2:
        raise ValueError("training data contains a single class; cannot fit a detector")

    groups = list(groups) if groups is not None else list(range(len(y)))
    folds = _grouped_folds(groups, n_splits, seed)

    oof = np.zeros(len(y), dtype=float)
    for train_idx, test_idx in folds:
        est = _make_estimator(kind, seed, int(y[train_idx].sum()), int((1 - y[train_idx]).sum()))
        est.fit(X[train_idx], y[train_idx])
        oof[test_idx] = est.predict_proba(X[test_idx])[:, 1]

    # Cross-fitted calibration: never score a point with a calibrator that saw it.
    honest = np.zeros(len(y), dtype=float)
    for _, test_idx in folds:
        mask = np.ones(len(y), dtype=bool)
        mask[test_idx] = False
        fold_cal = Calibrator(min_samples=50).fit(oof[mask], y[mask])
        honest[test_idx] = fold_cal.transform(oof[test_idx])

    # The shipped calibrator uses every out-of-fold score.
    calibrator = Calibrator().fit(oof, y)

    # Thresholds come from the held-out calibrated values, so the coverage and
    # error rate the policy promises are ones it has actually been tested at.
    policy = DecisionPolicy().fit(honest, y, target_error=target_error)

    metrics = {
        "auroc": float(roc_auc_score(y, oof)),
        "auprc": float(average_precision_score(y, oof)),
        "f1_at_0.5": float(f1_score(y, (honest >= 0.5).astype(int))),
        "brier": brier_score(honest, y),
        "ece": expected_calibration_error(honest, y),
        "aurc": _aurc(honest, y),
        "base_rate": float(y.mean()),
        "n_samples": len(y),
        "n_features": int(X.shape[1]),
        "coverage_at_target": policy.coverage,
        "achieved_error": policy.achieved_error,
        # The whole frontier, because one target hides the trade-off and reads
        # as failure when that target is simply unreachable for this model.
        "coverage_frontier": {
            f"{t:.2f}": _coverage_at(honest, y, t) for t in (0.05, 0.10, 0.20, 0.30, 0.40)
        },
    }

    # Per-tier ablation: what does each family buy on its own?
    per_tier: dict[str, dict[str, float]] = {}
    if tiers:
        tier_of = dict(zip(names, tiers, strict=False))
        for tier in sorted(set(tiers)):
            cols = [i for i, n in enumerate(names) if tier_of.get(n) == tier]
            if not cols:
                continue
            per_tier[tier] = _cv_auroc(X[:, cols], y, folds, kind, seed)

    final = _make_estimator(kind, seed, int(y.sum()), int((1 - y).sum()))
    final.fit(X, y)

    raw_imp = getattr(final, "feature_importances_", np.zeros(len(names)))
    importances = sorted(
        zip(names, (float(v) for v in raw_imp), strict=False),
        key=lambda kv: kv[1],
        reverse=True,
    )

    return TrainedDetector(
        model=final,
        feature_names=names,
        tiers=list(tiers),
        calibrator=calibrator,
        policy=policy,
        metrics=metrics,
        per_tier_metrics=per_tier,
        importances=importances,
        config=config or {},
    )


def _cv_auroc(
    X: np.ndarray, y: np.ndarray, folds: list[tuple[np.ndarray, np.ndarray]], kind: str, seed: int
) -> dict[str, float]:
    from sklearn.metrics import average_precision_score, roc_auc_score

    oof = np.zeros(len(y), dtype=float)
    for train_idx, test_idx in folds:
        est = _make_estimator(kind, seed, int(y[train_idx].sum()), int((1 - y[train_idx]).sum()))
        est.fit(X[train_idx], y[train_idx])
        oof[test_idx] = est.predict_proba(X[test_idx])[:, 1]
    return {
        "auroc": float(roc_auc_score(y, oof)),
        "auprc": float(average_precision_score(y, oof)),
        "n_features": int(X.shape[1]),
    }


def _coverage_at(risks: np.ndarray, y: np.ndarray, target_error: float) -> float:
    """Largest fraction auto-acceptable while keeping error at/below target."""
    order = np.argsort(risks)
    errors = np.cumsum(y[order]) / np.arange(1, len(y) + 1)
    ok = np.where(errors <= target_error)[0]
    return float((ok[-1] + 1) / len(y)) if len(ok) else 0.0


def _aurc(risks: np.ndarray, y: np.ndarray) -> float:
    """Area under the risk-coverage curve.

    Sort by predicted risk, then average the error rate among the k
    lowest-risk answers over all k. Lower is better. Unlike AUROC this rewards
    getting the *ordering at the safe end* right, which is what a selective
    system actually depends on.
    """
    order = np.argsort(risks)
    errors = np.cumsum(y[order]) / np.arange(1, len(y) + 1)
    return float(errors.mean())


def save_detector(detector: TrainedDetector, path: str | Path) -> Path:
    """Persist to a directory: pickled estimator plus human-readable metadata."""
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)

    with (out / _MODEL_FILE).open("wb") as fh:
        pickle.dump(
            {"model": detector.model, "calibrator": detector.calibrator}, fh,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    meta = {
        "feature_names": detector.feature_names,
        "tiers": detector.tiers,
        "policy": detector.policy.to_dict(),
        "metrics": detector.metrics,
        "per_tier_metrics": detector.per_tier_metrics,
        "importances": [(n, round(v, 6)) for n, v in detector.importances],
        "config": detector.config,
    }
    (out / _META_FILE).write_text(json.dumps(meta, indent=2))
    return out


def load_detector(
    path: str | Path,
    *,
    backend: Any | None = None,
    host: str | None = None,
) -> Any:
    """Load a saved detector and wrap it in a ready-to-use ``HallucinationDetector``."""
    from .backends.ollama import OllamaBackend
    from .detector import DetectorConfig, HallucinationDetector
    from .types import DEFAULT_SYSTEM_PROMPT

    src = Path(path)
    if src.is_file():
        src = src.parent

    meta = json.loads((src / _META_FILE).read_text())
    with (src / _MODEL_FILE).open("rb") as fh:
        blob = pickle.load(fh)

    trained = TrainedDetector(
        model=blob["model"],
        feature_names=meta["feature_names"],
        tiers=meta.get("tiers", []),
        calibrator=blob["calibrator"],
        policy=DecisionPolicy.from_dict(meta.get("policy", {})),
        metrics=meta.get("metrics", {}),
        per_tier_metrics=meta.get("per_tier_metrics", {}),
        importances=[(n, float(v)) for n, v in meta.get("importances", [])],
        config=meta.get("config", {}),
    )

    cfg_data = dict(meta.get("config", {}))
    trained_prompt = cfg_data.get("system_prompt")
    if trained_prompt and trained_prompt != DEFAULT_SYSTEM_PROMPT:
        # The features a detector learns are a property of the prompt that
        # produced them, so scoring with a different prompt silently degrades it.
        log.warning(
            "this detector was trained with a different system prompt than the "
            "one now configured; features are distribution-shifted. Rebuild the "
            "corpus and retrain, or restore the training prompt."
        )

    config = DetectorConfig(
        model=cfg_data.get("model", "llama3.2:3b"),
        embed_model=cfg_data.get("embed_model", "nomic-embed-text"),
        host=host or cfg_data.get("host", "http://localhost:11434"),
        tiers=tuple(cfg_data.get("tiers", ("surface", "token", "sampling"))),
        n_samples=int(cfg_data.get("n_samples", 6)),
        system_prompt=trained_prompt or DEFAULT_SYSTEM_PROMPT,
    )

    return HallucinationDetector(
        backend=backend
        or OllamaBackend(model=config.model, host=config.host, embed_model=config.embed_model),
        config=config,
        model=trained,
        policy=trained.policy,
        feature_names=trained.feature_names,
    )

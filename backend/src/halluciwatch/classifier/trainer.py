"""Hallucination fingerprint classifier training."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class TrainResult:
    """Results from classifier training."""
    model: Any
    scaler: StandardScaler
    metrics: Dict[str, float]
    feature_importance: Optional[np.ndarray] = None
    best_params: Optional[Dict] = None


def train_lightgbm(
    X: np.ndarray,
    y: np.ndarray,
    params: Optional[Dict] = None,
    n_folds: int = 5,
    random_state: int = 42,
) -> TrainResult:
    """Train a LightGBM classifier with stratified k-fold CV."""
    try:
        import lightgbm as lgb
    except ImportError:
        raise ImportError("Install lightgbm: pip install halluciwatch[train]")

    default_params = {
        "objective": "binary",
        "metric": "auc",
        "verbosity": -1,
        "n_estimators": 1000,
        "learning_rate": 0.05,
        "max_depth": 6,
        "num_leaves": 31,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "random_state": random_state,
    }
    if params:
        default_params.update(params)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    fold_metrics = []

    best_model = None
    best_auc = 0

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_scaled, y)):
        X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = lgb.LGBMClassifier(**default_params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.log_evaluation(0)],
        )

        y_pred = model.predict(X_val)
        y_proba = model.predict_proba(X_val)[:, 1]

        fold_auc = roc_auc_score(y_val, y_proba)
        fold_f1 = f1_score(y_val, y_pred)
        fold_metrics.append({"auc": fold_auc, "f1": fold_f1})

        if fold_auc > best_auc:
            best_auc = fold_auc
            best_model = model

        logger.info(f"Fold {fold+1}: AUC={fold_auc:.4f}, F1={fold_f1:.4f}")

    avg_metrics = {
        "auc": np.mean([m["auc"] for m in fold_metrics]),
        "f1": np.mean([m["f1"] for m in fold_metrics]),
        "precision": float(precision_score(y, best_model.predict(X_scaled))),
        "recall": float(recall_score(y, best_model.predict(X_scaled))),
        "accuracy": float(accuracy_score(y, best_model.predict(X_scaled))),
    }

    return TrainResult(
        model=best_model,
        scaler=scaler,
        metrics=avg_metrics,
        feature_importance=best_model.feature_importances_.astype(np.float64),
    )


def train_xgboost(
    X: np.ndarray,
    y: np.ndarray,
    params: Optional[Dict] = None,
    n_folds: int = 5,
    random_state: int = 42,
) -> TrainResult:
    """Train an XGBoost classifier with stratified k-fold CV."""
    try:
        import xgboost as xgb
    except ImportError:
        raise ImportError("Install xgboost: pip install halluciwatch[train]")

    default_params = {
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "tree_method": "hist",
        "n_estimators": 1000,
        "learning_rate": 0.05,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "random_state": random_state,
    }
    if params:
        default_params.update(params)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    fold_metrics = []

    best_model = None
    best_auc = 0

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_scaled, y)):
        X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = xgb.XGBClassifier(**default_params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        y_pred = model.predict(X_val)
        y_proba = model.predict_proba(X_val)[:, 1]

        fold_auc = roc_auc_score(y_val, y_proba)
        fold_f1 = f1_score(y_val, y_pred)
        fold_metrics.append({"auc": fold_auc, "f1": fold_f1})

        if fold_auc > best_auc:
            best_auc = fold_auc
            best_model = model

        logger.info(f"Fold {fold+1}: AUC={fold_auc:.4f}, F1={fold_f1:.4f}")

    avg_metrics = {
        "auc": np.mean([m["auc"] for m in fold_metrics]),
        "f1": np.mean([m["f1"] for m in fold_metrics]),
        "precision": float(precision_score(y, best_model.predict(X_scaled))),
        "recall": float(recall_score(y, best_model.predict(X_scaled))),
        "accuracy": float(accuracy_score(y, best_model.predict(X_scaled))),
    }

    return TrainResult(
        model=best_model,
        scaler=scaler,
        metrics=avg_metrics,
        feature_importance=best_model.feature_importances_.astype(np.float64),
    )


def train_sklearn_gbdt(
    X: np.ndarray,
    y: np.ndarray,
    n_folds: int = 5,
    random_state: int = 42,
) -> TrainResult:
    """Fallback: scikit-learn GradientBoosting (no external deps)."""
    from sklearn.ensemble import GradientBoostingClassifier

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    fold_metrics = []
    best_model = None
    best_auc = 0

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_scaled, y)):
        X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = GradientBoostingClassifier(
            n_estimators=200, learning_rate=0.1, max_depth=5, random_state=random_state
        )
        model.fit(X_train, y_train)

        y_proba = model.predict_proba(X_val)[:, 1]
        y_pred = model.predict(X_val)

        fold_auc = roc_auc_score(y_val, y_proba)
        fold_f1 = f1_score(y_val, y_pred)
        fold_metrics.append({"auc": fold_auc, "f1": fold_f1})

        if fold_auc > best_auc:
            best_auc = fold_auc
            best_model = model

    avg_metrics = {
        "auc": np.mean([m["auc"] for m in fold_metrics]),
        "f1": np.mean([m["f1"] for m in fold_metrics]),
        "precision": float(precision_score(y, best_model.predict(X_scaled))),
        "recall": float(recall_score(y, best_model.predict(X_scaled))),
        "accuracy": float(accuracy_score(y, best_model.predict(X_scaled))),
    }

    return TrainResult(
        model=best_model,
        scaler=scaler,
        metrics=avg_metrics,
    )


def save_model(result: TrainResult, path: Path, model_format: str = "json") -> None:
    """Save trained model and scaler."""
    path.mkdir(parents=True, exist_ok=True)

    # Save scaler
    import joblib
    joblib.dump(result.scaler, path / "scaler.joblib")

    # Save model
    model_path = path / "model"
    if hasattr(result.model, "booster"):
        # XGBoost or LightGBM
        try:
            result.model.save_model(str(model_path) + ".json")
        except Exception:
            joblib.dump(result.model, path / "model.joblib")
    else:
        joblib.dump(result.model, path / "model.joblib")

    # Save metrics
    with open(path / "metrics.json", "w") as f:
        json.dump(result.metrics, f, indent=2)

    # Save feature importance
    if result.feature_importance is not None:
        np.save(path / "feature_importance.npy", result.feature_importance)

    logger.info(f"Model saved to {path}")


def load_model(path: Path) -> Tuple[Any, StandardScaler]:
    """Load a saved model and scaler."""
    import joblib

    scaler = joblib.load(path / "scaler.joblib")

    # Try loading XGBoost/LightGBM JSON first
    json_model_path = path / "model.json"
    if json_model_path.exists():
        try:
            import xgboost as xgb
            model = xgb.XGBClassifier()
            model.load_model(str(json_model_path))
            return model, scaler
        except Exception:
            pass

    # Fallback to joblib
    joblib_path = path / "model.joblib"
    if joblib_path.exists():
        model = joblib.load(joblib_path)
        return model, scaler

    raise FileNotFoundError(f"No model found at {path}")

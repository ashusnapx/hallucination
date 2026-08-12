"""MLflow experiment tracking integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def setup_mlflow(
    experiment_name: str = "hallucination-fingerprinting",
    tracking_uri: Optional[str] = None,
) -> None:
    """Initialize MLflow experiment."""
    try:
        import mlflow
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        logger.info(f"MLflow experiment set: {experiment_name}")
    except ImportError:
        logger.warning("mlflow not installed. Install with: pip install mlflow")


def log_training_run(
    run_name: str,
    model: Any,
    metrics: Dict[str, float],
    params: Dict[str, Any],
    model_name: str = "lightgbm",
    artifact_dir: Optional[Path] = None,
) -> None:
    """Log a training run to MLflow."""
    try:
        import mlflow

        with mlflow.start_run(run_name=run_name):
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)

            # Log model
            if model_name == "xgboost":
                mlflow.xgboost.log_model(model, "model", model_format="json")
            elif model_name == "lightgbm":
                mlflow.lightgbm.log_model(model, "model")
            else:
                mlflow.sklearn.log_model(model, "model")

            if artifact_dir:
                mlflow.log_artifacts(str(artifact_dir))

            logger.info(f"MLflow run logged: {run_name}")
    except ImportError:
        logger.warning("mlflow not installed. Skipping logging.")
    except Exception as e:
        logger.error(f"MLflow logging failed: {e}")


def log_prediction(
    question: str,
    response: str,
    risk_score: float,
    label: Optional[int] = None,
) -> None:
    """Log a single prediction for monitoring."""
    try:
        import mlflow

        data = {
            "question": question,
            "response": response[:200],
            "risk_score": risk_score,
        }
        if label is not None:
            data["true_label"] = label

        mlflow.log_metrics({"risk_score": risk_score})
    except Exception:
        pass  # silent fail for prediction logging

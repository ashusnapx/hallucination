"""Training pipeline: load data, extract fingerprints, train classifier."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from halluciwatch.classifier.trainer import (
    save_model,
    train_lightgbm,
    train_sklearn_gbdt,
    train_xgboost,
)
from halluciwatch.datasets.loader import DatasetSample, get_all_datasets
from halluciwatch.fingerprint.builder import build_fingerprint

logger = logging.getLogger(__name__)


def prepare_fingerprints(
    samples: list[DatasetSample],
    model_name: str = "microsoft/DialoGPT-small",
    max_layers: int = 16,
    cache_dir: Optional[Path] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract fingerprints from all samples.

    For each sample, generates a response (or uses provided response),
    extracts neural signals, and builds a fingerprint vector.

    Returns:
        (X, y) where X is (n_samples, fingerprint_dim) and y is (n_samples,)
    """
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        raise ImportError("Install torch+transformers: pip install halluciwatch[torch]")

    # Check for cached fingerprints
    cache_path = cache_dir / f"fingerprints_{model_name.replace('/', '_')}.npz" if cache_dir else None
    if cache_path and cache_path.exists():
        logger.info(f"Loading cached fingerprints from {cache_path}")
        data = np.load(cache_path)
        return data["X"], data["y"]

    logger.info(f"Loading model {model_name} for fingerprint extraction...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        attn_implementation="eager",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )
    if torch.cuda.is_available():
        model = model.cuda()

    X_list = []
    y_list = []

    for i, sample in enumerate(samples):
        if (i + 1) % 50 == 0:
            logger.info(f"Processing sample {i+1}/{len(samples)}")

        text = f"Question: {sample.question}\nAnswer: {sample.response}"
        inputs = tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(
                **inputs,
                output_hidden_states=True,
                output_attentions=True,
                return_dict=True,
            )

        # Build signals manually from outputs
        from halluciwatch.signals.extractor import NeuralSignals, compute_entropy_from_logits

        logits = outputs.logits[0].cpu().float()
        entropy = compute_entropy_from_logits(logits).numpy()
        token_probs = torch.nn.functional.softmax(logits, dim=-1).max(dim=-1).values.numpy()

        attention_weights = [a[0].cpu().float().numpy() for a in outputs.attentions] if outputs.attentions else []
        hidden_states = [h[0].cpu().float().numpy() for h in outputs.hidden_states] if outputs.hidden_states else []

        signals = NeuralSignals(
            entropy=entropy,
            token_probs=token_probs,
            attention_weights=attention_weights,
            hidden_states=hidden_states,
            logits=logits.numpy(),
        )

        fingerprint = build_fingerprint(signals, max_layers=max_layers)
        X_list.append(fingerprint)
        y_list.append(sample.label)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)

    # Cache fingerprints
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez(cache_path, X=X, y=y)
        logger.info(f"Fingerprints cached to {cache_path}")

    return X, y


def run_training(
    model_name: str = "microsoft/DialoGPT-small",
    classifier: str = "lightgbm",
    output_dir: Path = Path("data/models/default"),
    data_dir: Optional[Path] = None,
    max_layers: int = 16,
) -> dict:
    """Full training pipeline.

    1. Load datasets
    2. Extract fingerprints
    3. Train classifier
    4. Save model

    Returns training metrics.
    """
    logging.basicConfig(level=logging.INFO)

    logger.info("=== HalluciWatch Training Pipeline ===")

    # Step 1: Load datasets
    logger.info("Step 1: Loading datasets...")
    samples = get_all_datasets(data_dir)
    logger.info(f"Loaded {len(samples)} samples")

    # Step 2: Extract fingerprints
    logger.info("Step 2: Extracting fingerprints...")
    X, y = prepare_fingerprints(samples, model_name, max_layers)
    logger.info(f"Fingerprints shape: {X.shape}, Labels distribution: {np.bincount(y)}")

    # Step 3: Train classifier
    logger.info(f"Step 3: Training {classifier} classifier...")
    if classifier == "lightgbm":
        result = train_lightgbm(X, y)
    elif classifier == "xgboost":
        result = train_xgboost(X, y)
    else:
        result = train_sklearn_gbdt(X, y)

    logger.info(f"Training metrics: {result.metrics}")

    # Step 4: Save model
    logger.info(f"Step 4: Saving model to {output_dir}...")
    save_model(result, output_dir, model_format=classifier)

    logger.info("=== Training Complete ===")
    return result.metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train HalluciWatch classifier")
    parser.add_argument("--model", default="microsoft/DialoGPT-small", help="HuggingFace model name")
    parser.add_argument("--classifier", default="lightgbm", choices=["lightgbm", "xgboost", "sklearn"])
    parser.add_argument("--output", default="data/models/default", help="Output directory")
    parser.add_argument("--max-layers", type=int, default=16)
    args = parser.parse_args()

    run_training(
        model_name=args.model,
        classifier=args.classifier,
        output_dir=Path(args.output),
        max_layers=args.max_layers,
    )

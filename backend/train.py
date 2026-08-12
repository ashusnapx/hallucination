"""Train HalluciWatch classifier on development data (no GPU needed)."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from halluciwatch.pipeline import run_training

if __name__ == "__main__":
    metrics = run_training(
        model_name="microsoft/DialoGPT-small",
        classifier="lightgbm",
        output_dir=Path("data/models/default"),
        max_layers=4,
    )
    print("\n=== Training Results ===")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

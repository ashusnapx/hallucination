"""Dataset loaders for HaluEval, TruthfulQA, SimpleQA, FEVER."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np


@dataclass
class DatasetSample:
    """A single labeled sample for hallucination detection."""
    question: str
    response: str
    label: int  # 0 = factual, 1 = hallucinated
    source: str  # dataset name
    metadata: Optional[dict] = None


def _download_if_needed(url: str, dest: Path) -> Path:
    """Download a file if it doesn't exist locally."""
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        import urllib.request
        print(f"Downloading {url} -> {dest}")
        urllib.request.urlretrieve(url, dest)
    except Exception as e:
        print(f"Warning: failed to download {url}: {e}")
    return dest


def load_halucalm(data_dir: Optional[Path] = None) -> List[DatasetSample]:
    """Load HaluEval dataset.

    Primary training dataset. 35K labeled hallucination samples.
    Source: https://github.com/RUCAIBox/HaluEval
    """
    data_dir = data_dir or Path("data/raw/halueval")
    samples = []

    # Try loading from local JSON files
    for json_file in data_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
            for item in data:
                if isinstance(item, dict):
                    question = item.get("question", item.get("query", ""))
                    response = item.get("hallucinated_answer", item.get("response", ""))
                    label = 1 if "hallucinated" in json_file.name.lower() else 0
                    samples.append(DatasetSample(
                        question=question,
                        response=response,
                        label=label,
                        source="haluéval",
                    ))
        except (json.JSONDecodeError, KeyError):
            continue

    # If no local files, generate synthetic samples for development
    if not samples:
        print("HaluEval data not found locally. Using development samples.")
        samples = _generate_halucalm_dev_samples()

    return samples


def _generate_halucalm_dev_samples() -> List[DatasetSample]:
    """Generate development samples when dataset isn't available."""
    factual = [
        ("What is the capital of France?", "The capital of France is Paris."),
        ("Who wrote Romeo and Juliet?", "William Shakespeare wrote Romeo and Juliet."),
        ("What year was the Eiffel Tower completed?", "The Eiffel Tower was completed in 1889."),
        ("What is the speed of light?", "The speed of light in vacuum is approximately 299,792,458 meters per second."),
        ("Who painted the Mona Lisa?", "Leonardo da Vinci painted the Mona Lisa."),
        ("What is the largest planet?", "Jupiter is the largest planet in our solar system."),
        ("When did World War II end?", "World War II ended in 1945."),
        ("What is DNA?", "DNA is a molecule that carries genetic instructions for life."),
        ("Who developed the theory of relativity?", "Albert Einstein developed the theory of relativity."),
        ("What is the chemical formula for water?", "The chemical formula for water is H2O."),
    ]

    hallucinated = [
        ("What is the capital of France?", "The capital of France is London."),
        ("Who wrote Romeo and Juliet?", "Charles Dickens wrote Romeo and Juliet."),
        ("What year was the Eiffel Tower completed?", "The Eiffel Tower was completed in 1902."),
        ("What is the speed of light?", "The speed of light is approximately 1 million meters per second."),
        ("Who painted the Mona Lisa?", "Pablo Picasso painted the Mona Lisa."),
        ("What is the largest planet?", "Saturn is the largest planet in our solar system."),
        ("When did World War II end?", "World War II ended in 1952."),
        ("What is DNA?", "DNA stands for Digital Network Architecture."),
        ("Who developed the theory of relativity?", "Isaac Newton developed the theory of relativity."),
        ("What is the chemical formula for water?", "The chemical formula for water is CO2."),
    ]

    samples = []
    for q, r in factual:
        samples.append(DatasetSample(question=q, response=r, label=0, source="haluéval-dev"))
    for q, r in hallucinated:
        samples.append(DatasetSample(question=q, response=r, label=1, source="haluéval-dev"))

    return samples


def load_truthfulqa(data_dir: Optional[Path] = None) -> List[DatasetSample]:
    """Load TruthfulQA dataset.

    817 adversarial questions across 38 domains.
    Access via HuggingFace: truthfulqa/truthful_qa
    """
    data_dir = data_dir or Path("data/raw/truthfulqa")
    samples = []

    # Try loading from local CSV/JSON
    for f in data_dir.glob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
            for item in data:
                samples.append(DatasetSample(
                    question=item.get("question", ""),
                    response=item.get("best_answer", item.get("correct_answer", "")),
                    label=0,
                    source="truthfulqa",
                    metadata={"category": item.get("category", "")},
                ))
        except (json.JSONDecodeError, KeyError):
            continue

    if not samples:
        print("TruthfulQA not found locally. Using development samples.")
        samples = _generate_truthfulqa_dev_samples()

    return samples


def _generate_truthfulqa_dev_samples() -> List[DatasetSample]:
    """Development samples for TruthfulQA."""
    qa_pairs = [
        ("What happens if you crack your knuckles?", "You may develop arthritis over time.", 1),
        ("What happens if you crack your knuckles?", "Nothing harmful happens; the sound is just gas bubbles.", 0),
        ("How many bones does a human have?", "A human has 306 bones.", 1),
        ("How many bones does a human have?", "An adult human has 206 bones.", 0),
        ("What is the largest ocean?", "The largest ocean is the Atlantic Ocean.", 1),
        ("What is the largest ocean?", "The Pacific Ocean is the largest ocean.", 0),
        ("Can gold be dissolved in water?", "Yes, gold dissolves easily in water.", 1),
        ("Can gold be dissolved in water?", "No, gold cannot be dissolved in water.", 0),
    ]

    samples = []
    for q, r, label in qa_pairs:
        samples.append(DatasetSample(
            question=q, response=r, label=label, source="truthfulqa-dev"
        ))
    return samples


def load_simpleqa(data_dir: Optional[Path] = None) -> List[DatasetSample]:
    """Load SimpleQA dataset.

    4,326 factual questions by OpenAI with single indisputable answers.
    Access: OpenEvals/SimpleQA on HuggingFace
    """
    data_dir = data_dir or Path("data/raw/simpleqa")
    samples = []

    for csv_file in data_dir.glob("*.csv"):
        try:
            with open(csv_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    samples.append(DatasetSample(
                        question=row.get("problem", ""),
                        response=row.get("answer", ""),
                        label=0,
                        source="simpleqa",
                        metadata={"topic": row.get("metadata", "")},
                    ))
        except Exception:
            continue

    if not samples:
        print("SimpleQA not found locally. Using development samples.")
        samples = _generate_simpleqa_dev_samples()

    return samples


def _generate_simpleqa_dev_samples() -> List[DatasetSample]:
    """Development samples for SimpleQA."""
    pairs = [
        ("What country is the Great Barrier Reef in?", "Australia"),
        ("What year was the first iPhone released?", "2007"),
        ("Who wrote 1984?", "George Orwell"),
        ("What is the smallest prime number?", "2"),
        ("What element has atomic number 79?", "Gold"),
    ]
    return [DatasetSample(question=q, response=r, label=0, source="simpleqa-dev") for q, r in pairs]


def load_fever(data_dir: Optional[Path] = None) -> List[DatasetSample]:
    """Load FEVER dataset.

    185,445 fact-verification claims.
    Labels: SUPPORTS, REFUTES, NOT_ENOUGH_INFO
    """
    data_dir = data_dir or Path("data/raw/fever")
    samples = []

    for jsonl_file in data_dir.glob("*.jsonl"):
        try:
            with open(jsonl_file) as f:
                for line in f:
                    item = json.loads(line)
                    label_str = item.get("label", "").upper()
                    label = 1 if label_str == "REFUTES" else 0
                    samples.append(DatasetSample(
                        question=item.get("claim", ""),
                        response=item.get("claim", ""),
                        label=label,
                        source="fever",
                        metadata={"evidence": item.get("evidence", [])},
                    ))
        except (json.JSONDecodeError, KeyError):
            continue

    if not samples:
        print("FEVER not found locally. Using development samples.")
        samples = _generate_fever_dev_samples()

    return samples


def _generate_fever_dev_samples() -> List[DatasetSample]:
    """Development samples for FEVER."""
    claims = [
        ("The Earth orbits the Sun.", 0),
        ("The Moon is made of cheese.", 1),
        ("Water boils at 100C at sea level.", 0),
        ("Humans can breathe underwater without equipment.", 1),
        ("The Pacific Ocean is the largest ocean.", 0),
    ]
    return [DatasetSample(question=c, response=c, label=l, source="fever-dev") for c, l in claims]


def get_all_datasets(data_dir: Optional[Path] = None) -> List[DatasetSample]:
    """Load all available datasets and combine them."""
    data_dir = data_dir or Path("data/raw")
    all_samples = []
    all_samples.extend(load_halucalm(data_dir / "haluéval"))
    all_samples.extend(load_truthfulqa(data_dir / "truthfulqa"))
    all_samples.extend(load_simpleqa(data_dir / "simpleqa"))
    all_samples.extend(load_fever(data_dir / "fever"))
    return all_samples

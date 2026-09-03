"""HalluciWatch - real-time hallucination risk scoring for local LLMs.

Reads the signals a model emits while generating - the shape of its token
probability distribution, and how much its answer changes when you ask again -
and turns them into a calibrated risk score *before* the answer reaches the
user. No external fact-checking service, no retrieval index, no cloud API: the
model runs on your machine through Ollama and scores itself.

Quick start::

    from halluciwatch import HallucinationDetector

    with HallucinationDetector() as detector:
        report = detector.score("Who was the 14th person to walk on the Moon?")
        print(report.risk, report.decision)
        print(report.answer)

For a calibrated score, train on your own model first::

    halluciwatch build --model llama3.2:3b --limit 300 --out data/corpus.jsonl
    halluciwatch train --corpus data/corpus.jsonl --out models/detector
    halluciwatch score "Who discovered penicillin?" --model-dir models/detector
"""

from __future__ import annotations

__version__ = "0.2.0"

from .backends.ollama import OllamaBackend, OllamaError, OllamaOptions
from .calibration import Calibrator, DecisionPolicy
from .cluster import cluster_answers, normalise_answer, semantic_entropy
from .detector import DetectorConfig, HallucinationDetector
from .features import build_fingerprint, feature_names
from .types import Fingerprint, Generation, RiskReport, Tier, TokenLogprob

__all__ = [
    "Calibrator",
    "DecisionPolicy",
    "DetectorConfig",
    "Fingerprint",
    "Generation",
    "HallucinationDetector",
    "OllamaBackend",
    "OllamaError",
    "OllamaOptions",
    "RiskReport",
    "Tier",
    "TokenLogprob",
    "__version__",
    "build_fingerprint",
    "cluster_answers",
    "feature_names",
    "normalise_answer",
    "semantic_entropy",
]

"""Tests for signal extraction and fingerprint building."""

import numpy as np
import pytest

from halluciwatch.signals.extractor import NeuralSignals, compute_entropy_from_logits
from halluciwatch.fingerprint.builder import build_fingerprint, get_fingerprint_dim


def test_compute_entropy():
    """Test entropy computation from logits."""
    import torch

    # Certain prediction (low entropy)
    logits_certain = torch.tensor([[10.0, 0.1, 0.1]])
    entropy_certain = compute_entropy_from_logits(logits_certain)
    assert entropy_certain.item() < 0.5

    # Uncertain prediction (high entropy)
    logits_uncertain = torch.tensor([[1.0, 1.0, 1.0]])
    entropy_uncertain = compute_entropy_from_logits(logits_uncertain)
    assert entropy_uncertain.item() > 1.0


def test_build_fingerprint():
    """Test fingerprint vector construction."""
    signals = NeuralSignals(
        entropy=np.random.rand(20).astype(np.float32),
        token_probs=np.random.rand(20).astype(np.float32),
        attention_weights=[np.random.rand(8, 20, 20).astype(np.float32) for _ in range(4)],
        hidden_states=[np.random.rand(20, 64).astype(np.float32) for _ in range(4)],
        logits=np.random.rand(20, 100).astype(np.float32),
    )

    fingerprint = build_fingerprint(signals, max_layers=4)
    assert isinstance(fingerprint, np.ndarray)
    assert fingerprint.ndim == 1
    assert len(fingerprint) > 0
    assert not np.any(np.isnan(fingerprint))


def test_fingerprint_dim():
    """Test that fingerprint dimension is consistent."""
    dim1 = get_fingerprint_dim(max_layers=4)
    dim2 = get_fingerprint_dim(max_layers=4)
    assert dim1 == dim2


def test_neural_signals_properties():
    """Test NeuralSignals dataclass."""
    signals = NeuralSignals(
        entropy=np.zeros(10),
        token_probs=np.zeros(10),
        attention_weights=[np.zeros((8, 10, 10)) for _ in range(3)],
        hidden_states=[np.zeros((10, 64)) for _ in range(3)],
        logits=np.zeros((10, 100)),
    )
    assert signals.num_layers == 3
    assert signals.seq_len == 10

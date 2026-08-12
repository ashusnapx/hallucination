"""Build fixed-length hallucination fingerprint vectors from neural signals."""

from __future__ import annotations

from typing import List

import numpy as np

from halluciwatch.signals.extractor import NeuralSignals


def _layer_entropy_stats(signals: NeuralSignals) -> List[float]:
    """Per-layer entropy statistics."""
    stats = []
    for hs in signals.hidden_states:
        # Compute entropy of the hidden state projection via PCA-like approach
        # Use variance across features as a proxy for information content
        variance = np.var(hs, axis=-1).mean()
        stats.extend([float(np.mean(hs)), float(variance), float(np.max(np.abs(hs)))])
    return stats


def _attention_stats(signals: NeuralSignals) -> List[float]:
    """Per-layer attention pattern statistics."""
    stats = []
    for attn in signals.attention_weights:
        # attn shape: (num_heads, seq, seq)
        # Attention entropy per head
        attn_clipped = np.clip(attn, 1e-10, 1.0)
        attn_entropy = -np.sum(attn_clipped * np.log2(attn_clipped + 1e-10), axis=-1)
        stats.extend([
            float(attn_entropy.mean()),      # mean attention entropy
            float(attn_entropy.max()),        # max attention entropy
            float(np.mean(attn)),             # mean attention weight
            float(np.std(attn)),              # attention concentration
        ])

        # Spectral features: top eigenvalues of attention matrix (LapEigvals)
        for head in range(min(attn.shape[0], 4)):  # first 4 heads only
            attn_matrix = attn[head]
            try:
                eigenvalues = np.linalg.eigvalsh(attn_matrix)
                top_k = np.sort(np.abs(eigenvalues))[-3:]
                stats.extend([float(v) for v in top_k])
            except np.linalg.LinAlgError:
                stats.extend([0.0, 0.0, 0.0])

    return stats


def _token_level_stats(signals: NeuralSignals) -> List[float]:
    """Token-level entropy and probability statistics."""
    return [
        float(np.mean(signals.entropy)),           # mean entropy
        float(np.max(signals.entropy)),             # max entropy (peak uncertainty)
        float(np.std(signals.entropy)),             # entropy variance
        float(np.median(signals.entropy)),          # median entropy
        float(np.mean(signals.token_probs)),        # mean max-prob
        float(np.min(signals.token_probs)),         # min max-prob (weakest prediction)
        float(np.std(signals.token_probs)),         # prob variance
    ]


def _cross_layer_features(signals: NeuralSignals) -> List[float]:
    """Cross-layer statistics and deltas."""
    if len(signals.hidden_states) < 2:
        return [0.0] * 10

    layer_norms = [float(np.linalg.norm(hs.mean(axis=0))) for hs in signals.hidden_states]
    deltas = [layer_norms[i+1] - layer_norms[i] for i in range(len(layer_norms) - 1)]

    return [
        float(np.mean(layer_norms)),
        float(np.std(layer_norms)),
        float(np.max(layer_norms)),
        float(np.min(layer_norms)),
        float(np.mean(deltas)),
        float(np.std(deltas)),
        float(np.max(deltas)),
        float(np.min(deltas)),
        layer_norms[0] if layer_norms else 0.0,   # first layer norm
        layer_norms[-1] if layer_norms else 0.0,   # last layer norm
    ]


def _eigenvalue_features(signals: NeuralSignals) -> List[float]:
    """Eigenvalue decomposition of hidden state covariance (INSIDE/EigenScore)."""
    features = []
    for hs in signals.hidden_states[:4]:  # first 4 layers
        try:
            # Center and compute covariance
            centered = hs - hs.mean(axis=0, keepdims=True)
            cov = np.cov(centered.T) if centered.shape[1] > 1 else np.array([[1.0]])
            eigenvalues = np.linalg.eigvalsh(cov)
            eigenvalues = np.sort(np.abs(eigenvalues))[::-1]
            top5 = eigenvalues[:5]
            features.extend([float(v) for v in top5])
            # Ratio of top eigenvalues
            total = eigenvalues.sum()
            features.append(float(top5[0] / total) if total > 0 else 0.0)
        except (np.linalg.LinAlgError, ValueError):
            features.extend([0.0] * 6)

    return features


def build_fingerprint(signals: NeuralSignals, max_layers: int = 32) -> np.ndarray:
    """Build a fixed-length fingerprint vector from neural signals.

    Concatenates:
    - Per-layer entropy stats
    - Per-layer attention stats
    - Token-level statistics
    - Cross-layer features
    - Eigenvalue features

    Returns a 1D numpy array (the fingerprint).
    """
    features = []

    # Limit layers for consistent vector length
    # Pad if fewer layers than max_layers
    layer_count = min(len(signals.hidden_states), max_layers)

    features.extend(_token_level_stats(signals))
    features.extend(_cross_layer_features(signals))
    features.extend(_eigenvalue_features(signals))

    # Per-layer features (padded to max_layers)
    for i in range(max_layers):
        if i < layer_count:
            hs = signals.hidden_states[i]
            features.extend([
                float(np.mean(hs)),
                float(np.var(hs)),
                float(np.max(np.abs(hs))),
            ])
        else:
            features.extend([0.0, 0.0, 0.0])

    for i in range(max_layers):
        if i < len(signals.attention_weights):
            attn = signals.attention_weights[i]
            attn_entropy = -np.sum(np.clip(attn, 1e-10, 1.0) * np.log2(np.clip(attn, 1e-10, 1.0) + 1e-10), axis=-1)
            features.extend([
                float(attn_entropy.mean()),
                float(np.mean(attn)),
                float(np.std(attn)),
            ])
        else:
            features.extend([0.0, 0.0, 0.0])

    return np.array(features, dtype=np.float32)


def get_fingerprint_dim(max_layers: int = 32) -> int:
    """Return the expected fingerprint dimensionality."""
    dummy_signals = NeuralSignals(
        entropy=np.zeros(10),
        token_probs=np.zeros(10),
        attention_weights=[np.zeros((8, 10, 10)) for _ in range(max_layers)],
        hidden_states=[np.zeros((10, 64)) for _ in range(max_layers)],
        logits=np.zeros((10, 100)),
    )
    return len(build_fingerprint(dummy_signals, max_layers=max_layers))

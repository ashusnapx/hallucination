"""PyTorch hooks and built-in HF flags for extracting internal neural signals."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F


@dataclass
class NeuralSignals:
    """Container for all extracted signals from a single forward pass."""

    entropy: np.ndarray                  # (seq_len,) per-token entropy in bits
    token_probs: np.ndarray             # (seq_len,) max prob per token
    attention_weights: List[np.ndarray]  # list of (num_heads, seq, seq) per layer
    hidden_states: List[np.ndarray]      # list of (seq, hidden) per layer
    logits: np.ndarray                   # (seq_len, vocab_size)

    @property
    def num_layers(self) -> int:
        return len(self.hidden_states)

    @property
    def seq_len(self) -> int:
        return len(self.entropy)


def compute_entropy_from_logits(logits: torch.Tensor) -> torch.Tensor:
    """Shannon entropy in bits from logits. Shape: (..., vocab_size) -> (...)."""
    probs = F.softmax(logits, dim=-1)
    log_probs = torch.log2(probs.clamp(min=1e-12))
    return -(probs * log_probs).sum(dim=-1)


def extract_signals(
    model: Any,
    input_ids: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
) -> NeuralSignals:
    """Run a forward pass and extract all neural signals.

    Uses HuggingFace's built-in output_hidden_states and output_attentions flags.
    Requires attn_implementation="eager" for attention weight extraction.
    """
    was_training = model.training
    model.eval()

    with torch.no_grad():
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            output_hidden_states=True,
            output_attentions=True,
            return_dict=True,
        )

    logits = outputs.logits[0].cpu().float()  # (seq, vocab)
    entropy = compute_entropy_from_logits(logits).numpy()  # (seq,)
    token_probs = F.softmax(logits, dim=-1).max(dim=-1).values.numpy()  # (seq,)

    attention_weights = []
    if outputs.attentions is not None:
        for attn in outputs.attentions:
            # (batch=0, :, :, :) -> (num_heads, seq, seq)
            attention_weights.append(attn[0].cpu().float().numpy())

    hidden_states = []
    if outputs.hidden_states is not None:
        for hs in outputs.hidden_states:
            hidden_states.append(hs[0].cpu().float().numpy())  # (seq, hidden)

    if was_training:
        model.train()

    return NeuralSignals(
        entropy=entropy,
        token_probs=token_probs,
        attention_weights=attention_weights,
        hidden_states=hidden_states,
        logits=logits.numpy(),
    )


def extract_signals_with_hooks(
    model: Any,
    input_ids: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
) -> NeuralSignals:
    """Alternative: use raw PyTorch forward hooks for models without built-in flags.

    Registers hooks on every decoder layer to capture hidden states and attention.
    """
    activations: Dict[int, torch.Tensor] = {}
    attention_outs: Dict[int, torch.Tensor] = {}

    def hook_hidden(module, input, output):
        idx = getattr(module, "layer_idx", len(activations))
        activations[idx] = output[0].detach().cpu() if isinstance(output, tuple) else output.detach().cpu()

    def hook_attention(module, input, output):
        idx = getattr(module, "layer_idx", len(attention_outs))
        if isinstance(output, tuple) and len(output) > 1 and output[1] is not None:
            attention_outs[idx] = output[1][0].detach().cpu()  # (heads, seq, seq)

    hooks = []
    try:
        for i, layer in enumerate(model.model.layers):
            layer.layer_idx = i
            hooks.append(layer.register_forward_hook(hook_hidden))
            hooks.append(layer.self_attn.register_forward_hook(hook_attention))
    except AttributeError:
        # Non-HF model or different architecture — fall back to built-in flags
        for h in hooks:
            h.remove()
        return extract_signals(model, input_ids, attention_mask)

    was_training = model.training
    model.eval()

    with torch.no_grad():
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            return_dict=True,
        )

    for h in hooks:
        h.remove()

    logits = outputs.logits[0].cpu().float()
    entropy = compute_entropy_from_logits(logits).numpy()
    token_probs = F.softmax(logits, dim=-1).max(dim=-1).values.numpy()

    hidden_states = [activations[i].numpy() for i in sorted(activations.keys())]
    attention_weights = [attention_outs[i].numpy() for i in sorted(attention_outs.keys())]

    if was_training:
        model.train()

    return NeuralSignals(
        entropy=entropy,
        token_probs=token_probs,
        attention_weights=attention_weights,
        hidden_states=hidden_states,
        logits=logits.numpy(),
    )

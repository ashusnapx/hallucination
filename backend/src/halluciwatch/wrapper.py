"""HalluciWatch — Main wrapper class for real-time hallucination risk scoring."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from halluciwatch.classifier.trainer import load_model
from halluciwatch.fingerprint.builder import build_fingerprint
from halluciwatch.signals.extractor import NeuralSignals, extract_signals

logger = logging.getLogger(__name__)


class HalluciWatch:
    """Real-time hallucination risk detection wrapper for any HuggingFace LLM.

    Usage:
        from halluciwatch import HalluciWatch

        hw = HalluciWatch.from_pretrained("meta-llama/Llama-3.1-8B")
        response, risk_score = hw.score("What year was the Eiffel Tower completed?")
    """

    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        classifier_path: Optional[Path] = None,
        risk_threshold: float = 0.7,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.risk_threshold = risk_threshold
        self.last_risk_score: float = 0.0
        self.last_signals: Optional[Dict] = None

        # Load trained classifier
        self.classifier = None
        self.scaler = None
        if classifier_path and classifier_path.exists():
            try:
                self.classifier, self.scaler = load_model(classifier_path)
                logger.info(f"Classifier loaded from {classifier_path}")
            except Exception as e:
                logger.warning(f"Could not load classifier: {e}. Using heuristic scoring.")

    @classmethod
    def from_pretrained(
        cls,
        model_name: str,
        classifier_path: Optional[Path] = None,
        device: Optional[str] = None,
        **model_kwargs,
    ) -> "HalluciWatch":
        """Load a model and create a HalluciWatch instance."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError:
            raise ImportError("Install transformers: pip install halluciwatch[torch]")

        import torch

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"Loading model {model_name} on {device}...")

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            attn_implementation="eager",  # Required for attention weight extraction
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map=device if device == "cuda" else None,
            **model_kwargs,
        )

        if device == "cpu":
            model = model.to(device)

        return cls(model, tokenizer, classifier_path)

    def generate(self, prompt: str, max_new_tokens: int = 256, **kwargs) -> str:
        """Generate a response to a prompt."""
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                **kwargs,
            )

        # Decode only the new tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)

    def _score_from_signals(self, signals: NeuralSignals) -> float:
        """Compute risk score from neural signals."""
        if self.classifier is not None and self.scaler is not None:
            # Use trained classifier
            fingerprint = build_fingerprint(signals)
            X = self.scaler.transform(fingerprint.reshape(1, -1))
            proba = self.classifier.predict_proba(X)[0]
            return float(proba[1])  # probability of hallucination class
        else:
            # Heuristic scoring based on signal analysis
            return self._heuristic_score(signals)

    def _heuristic_score(self, signals: NeuralSignals) -> float:
        """Fallback heuristic scoring without a trained classifier.

        Based on research findings:
        - High entropy → more uncertain → higher hallucination risk
        - Low attention concentration → scattered attention → higher risk
        - Erratic hidden state patterns → higher risk
        """
        scores = []

        # Entropy score: higher entropy = higher risk
        mean_entropy = float(np.mean(signals.entropy))
        max_entropy = float(np.max(signals.entropy))
        # Normalize: entropy > 3 bits is very uncertain
        entropy_score = min(1.0, (mean_entropy / 3.0) * 0.5 + (max_entropy / 5.0) * 0.5)
        scores.append(entropy_score)

        # Attention score: lower concentration = higher risk
        if signals.attention_weights:
            attn_concentrations = []
            for attn in signals.attention_weights:
                # Attention concentration: how focused is attention
                concentration = float(np.max(attn, axis=-1).mean())
                attn_concentrations.append(concentration)
            mean_concentration = np.mean(attn_concentrations)
            # Low concentration = high risk
            attn_score = 1.0 - min(1.0, mean_concentration)
            scores.append(attn_score)

        # Hidden state stability: erratic patterns = higher risk
        if len(signals.hidden_states) >= 2:
            layer_deltas = []
            for i in range(len(signals.hidden_states) - 1):
                delta = np.mean(np.abs(
                    signals.hidden_states[i+1] - signals.hidden_states[i]
                ))
                layer_deltas.append(float(delta))
            mean_delta = np.mean(layer_deltas)
            # High delta between layers = erratic = higher risk
            stability_score = min(1.0, mean_delta / 2.0)
            scores.append(stability_score)

        return float(np.mean(scores)) if scores else 0.5

    def score(self, prompt: str, max_new_tokens: int = 256) -> Tuple[str, float]:
        """Generate a response and score its hallucination risk.

        Returns:
            (response_text, risk_score) where risk_score is 0.0 (safe) to 1.0 (high risk)
        """
        response = self.generate(prompt, max_new_tokens)
        risk_score = self.score_pair(prompt, response)[0]
        return response, risk_score

    def score_pair(self, question: str, response: str) -> Tuple[float, Dict]:
        """Score a question-response pair without generating.

        Returns:
            (risk_score, signals_dict)
        """
        import torch

        # Tokenize the full conversation
        full_text = f"Question: {question}\nAnswer: {response}"
        inputs = self.tokenizer(full_text, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        signals = extract_signals(self.model, inputs["input_ids"], inputs.get("attention_mask"))
        risk_score = self._score_from_signals(signals)

        self.last_risk_score = risk_score
        self.last_signals = {
            "entropy_mean": float(np.mean(signals.entropy)),
            "entropy_max": float(np.max(signals.entropy)),
            "num_layers": signals.num_layers,
            "seq_len": signals.seq_len,
        }

        return risk_score, self.last_signals

    def score_streaming(
        self, prompt: str, max_new_tokens: int = 256
    ):
        """Stream tokens with live risk scoring.

        Yields:
            (token_text, cumulative_risk_score)
        """
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        generated_tokens = []

        with torch.no_grad():
            for _ in range(max_new_tokens):
                outputs = self.model(**inputs)
                next_token_logits = outputs.logits[0, -1, :]
                next_token = torch.argmax(next_token_logits, dim=-1)

                if next_token.item() == self.tokenizer.eos_token_id:
                    break

                token_text = self.tokenizer.decode(next_token, skip_special_tokens=True)
                generated_tokens.append(token_text)

                # Score current state
                full_text = prompt + "".join(generated_tokens)
                full_inputs = self.tokenizer(full_text, return_tensors="pt")
                full_inputs = {k: v.to(self.model.device) for k, v in full_inputs.items()}
                signals = extract_signals(self.model, full_inputs["input_ids"])
                risk = self._score_from_signals(signals)

                # Update input for next iteration
                inputs["input_ids"] = torch.cat([
                    inputs["input_ids"], next_token.unsqueeze(0).unsqueeze(0)
                ], dim=-1)
                if "attention_mask" in inputs:
                    inputs["attention_mask"] = torch.cat([
                        inputs["attention_mask"],
                        torch.ones(1, 1, device=inputs["attention_mask"].device),
                    ], dim=-1)

                yield token_text, risk

    def as_langchain_llm(self, **kwargs):
        """Return a LangChain-compatible LLM wrapper."""
        try:
            from langchain_huggingface import HuggingFacePipeline
            from transformers import pipeline as hf_pipeline

            pipe = hf_pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                **kwargs,
            )
            return HuggingFacePipeline(pipeline=pipe)
        except ImportError:
            raise ImportError("Install langchain: pip install halluciwatch[langchain]")

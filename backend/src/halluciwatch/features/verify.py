"""Tier-3 features: asking the model to judge its own answer.

``P(True)`` (Kadavath et al. 2022) re-presents the question and answer and reads
the probability mass the model puts on "correct" at the first generated token.

.. warning::

   **This tier is off by default, because it does not work on small models.**
   Measured on llama3.2:1b over 40 TriviaQA questions, P(True) reached
   AUROC 0.500 - exactly chance - with mean 0.527 on correct answers and 0.530
   on wrong ones. Adding it to the tier-1 feature set *reduced* cross-validated
   AUROC from 0.872 to 0.841, because an uninformative feature is not free: it
   gives the classifier noise to overfit.

   This is consistent with the original paper, where self-evaluation ability
   emerges with scale. Enable this tier only after ``halluciwatch ablate``
   shows it earns its place for your model. The ablation report exists precisely
   so this decision is made from data rather than from the literature's default.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ..types import Tier
from .registry import feature

if TYPE_CHECKING:
    from ..backends.ollama import OllamaBackend

__all__ = ["VERIFY_FEATURES", "p_true", "verify_features"]

_V = Tier.VERIFY

VERIFY_FEATURES = [
    feature(
        "vrf.p_true", _V,
        "Model's own probability that its answer is correct (Kadavath et al.). "
        "Near-chance on sub-3B models - see module docstring.",
        higher_is_riskier=False,
    ),
    feature(
        "vrf.p_true_margin", _V,
        "|P(correct) - P(incorrect)|; low means the judge itself is undecided.",
        higher_is_riskier=False,
    ),
]

_PROMPT = (
    "Question: {question}\n"
    "Proposed answer: {answer}\n\n"
    "Is the proposed answer factually correct? Reply with exactly one letter.\n"
    "A) correct\n"
    "B) incorrect\n"
    "Answer:"
)


def p_true(backend: OllamaBackend, question: str, answer: str) -> tuple[float, float]:
    """Return ``(p_correct, margin)``.

    Reads the renormalised mass on the ``A``/``B`` tokens at the first generated
    position rather than parsing the text, so a chatty model that says
    "A) correct, because..." still scores correctly. Returns ``(0.5, 0.0)`` -
    maximally uninformative - if the letters do not appear in the top-k.
    """
    from ..backends.ollama import OllamaOptions

    gen = backend.generate(
        _PROMPT.format(question=question, answer=answer),
        options=OllamaOptions(temperature=0.0, seed=42, num_predict=1),
        logprobs=True,
        top_logprobs=20,
    )
    if not gen.tokens:
        return 0.5, 0.0

    p_a = p_b = 0.0
    for token, logprob in gen.tokens[0].top_logprobs:
        head = token.strip().upper()[:1]
        if head == "A":
            p_a += math.exp(logprob)
        elif head == "B":
            p_b += math.exp(logprob)

    total = p_a + p_b
    if total <= 0:
        return 0.5, 0.0
    p_correct = p_a / total
    return p_correct, abs(p_correct - (1.0 - p_correct))


def verify_features(backend: OllamaBackend, question: str, answer: str) -> dict[str, float]:
    try:
        p_correct, margin = p_true(backend, question, answer)
    except Exception:
        p_correct, margin = 0.5, 0.0
    return {"vrf.p_true": p_correct, "vrf.p_true_margin": margin}

"""Tier-0 features: free lexical signals computed from the answer text alone.

The important one here is refusal detection. In the pilot, the question "what
was the exact street address of the first Starbucks franchise in Nepal?" scored
a *semantic entropy of 0.0* - not because the model was confident in a fact, but
because it consistently refused to answer. Consistent refusal is
indistinguishable from consistent knowledge to every consistency-based signal,
so it has to be measured separately or the detector inherits a blind spot on
precisely the questions it most needs to handle.
"""

from __future__ import annotations

import re

from ..types import Tier
from .registry import feature

__all__ = ["SURFACE_FEATURES", "looks_like_refusal", "surface_features"]

_S = Tier.SURFACE

SURFACE_FEATURES = [
    feature(
        "srf.is_refusal", _S,
        "The answer declines to answer. Refusals are honest, not hallucinated, but "
        "they look maximally confident to consistency-based signals.",
        higher_is_riskier=False,
    ),
    feature("srf.hedge_count", _S, "Count of hedging markers ('possibly', 'I think', 'roughly')."),
    feature("srf.hedge_density", _S, "Hedges per word."),
    feature(
        "srf.n_words", _S, "Answer length in words.", higher_is_riskier=False,
    ),
    feature(
        "srf.digit_density", _S,
        "Share of characters that are digits. Specific numbers are high-risk claims.",
    ),
    feature(
        "srf.n_entities", _S,
        "Count of capitalised mid-sentence tokens, a cheap proxy for named entities.",
    ),
    feature("srf.n_sentences", _S, "Number of sentences."),
    feature(
        "srf.mean_word_len", _S, "Mean word length, a weak proxy for register/specificity.",
    ),
]

# Ordered longest-first so that "i do not have access" wins over "i do not".
_REFUSAL_PATTERNS = (
    # "I'm" has no space before the clitic, so the contraction alternative must
    # not require one: i(?:\s+am|'m), never i (?:am|'m).
    r"i(?:\s+do\s+not|\s*don'?t)\s+have\s+"
    r"(?:access|any information|enough information|the ability)",
    r"i(?:\s+am|'m)\s+not\s+(?:aware|able|sure|certain)",
    r"i\s+(?:cannot|can'?t|can not)\s+(?:provide|find|answer|confirm|verify|determine)",
    r"i(?:\s+do\s+not|\s*don'?t)\s+(?:know|have)",
    r"(?:there is|there's) no (?:record|information|evidence|such)",
    r"i\s+(?:could\s+not|couldn'?t)\s+find",
    r"unable to (?:provide|find|answer|determine|verify)",
    r"no (?:information|data|record) (?:is )?available",
    r"(?:sorry|apolog)",
    r"as an ai",
    r"insufficient information",
)
_REFUSAL_RE = re.compile("|".join(_REFUSAL_PATTERNS), re.IGNORECASE)

_HEDGES = (
    "possibly", "probably", "perhaps", "maybe", "might", "may be", "could be",
    "i think", "i believe", "approximately", "roughly", "around", "about",
    "seems", "appears", "likely", "unlikely", "presumably", "arguably",
    "not certain", "not sure", "as far as i know", "if i recall",
)
_HEDGE_RE = re.compile("|".join(re.escape(h) for h in _HEDGES), re.IGNORECASE)

_SENTENCE_RE = re.compile(r"[.!?]+(?:\s|$)")
_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def looks_like_refusal(text: str) -> bool:
    """Heuristic refusal detector.

    Deliberately a regex rather than a model call: it must be free, or the tier-0
    guarantee is broken. It is a heuristic and will miss creative phrasings; the
    classifier treats it as one feature among many rather than a hard gate.
    """
    return bool(_REFUSAL_RE.search(text))


def surface_features(answer: str) -> dict[str, float]:
    text = answer.strip()
    words = _WORD_RE.findall(text)
    n_words = len(words)

    # Skip index 0: a capitalised first word is just sentence case, not an entity.
    entities = sum(1 for w in words[1:] if w[:1].isupper())
    sentences = [s for s in _SENTENCE_RE.split(text) if s.strip()]
    hedges = len(_HEDGE_RE.findall(text))
    digits = sum(ch.isdigit() for ch in text)

    return {
        "srf.is_refusal": float(looks_like_refusal(text)),
        "srf.hedge_count": float(hedges),
        "srf.hedge_density": hedges / n_words if n_words else 0.0,
        "srf.n_words": float(n_words),
        "srf.digit_density": digits / len(text) if text else 0.0,
        "srf.n_entities": float(entities),
        "srf.n_sentences": float(len(sentences)),
        "srf.mean_word_len": sum(len(w) for w in words) / n_words if n_words else 0.0,
    }

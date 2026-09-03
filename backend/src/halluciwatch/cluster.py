"""Semantic clustering of sampled answers.

Semantic entropy (Kuhn et al. 2023; Farquhar et al., *Nature* 2024) measures
uncertainty over *meanings* rather than *strings*: sample the model several
times, group answers that mean the same thing, and take the entropy of the
resulting cluster distribution. "Paris" and "It is Paris" are one meaning;
"Paris" and "Lyon" are two.

The grouping step is where implementations quietly go wrong. Two notes from
building this one:

* Embedding cosine on **short entity answers is weak**. Person names occupy a
  tight cone in embedding space, so "John Logie Baird" and "Philo Farnsworth"
  sit at 0.40 cosine even after the lower-casing fix - closer than many true
  paraphrases. Exact match on a normalised string is both cheaper and more
  reliable for short answers, so it is tried first.
* In the pilot, a pure-embedding clusterer at threshold 0.85 over-split badly
  (5.8 clusters from 7 samples), which flattened semantic entropy into noise.
"""

from __future__ import annotations

import math
import re
import string
from collections.abc import Callable, Sequence
from dataclasses import dataclass

__all__ = ["ClusterResult", "cluster_answers", "normalise_answer", "semantic_entropy"]

_ARTICLES = re.compile(r"\b(a|an|the)\b")
_PUNCT = str.maketrans("", "", string.punctuation)
_WS = re.compile(r"\s+")

# Sentinel normalised form that every refusal maps onto, so "I don't know" and
# "I have no information on that" land in one cluster. Chosen so no real answer
# can normalise to it.
_REFUSAL_KEY = "\x00refusal"

# Leading filler that models put in front of short answers. Stripped so that
# "The answer is Paris" and "Paris" land in the same cluster.
_PREAMBLE = re.compile(
    r"^(?:the\s+)?(?:answer\s+is|correct\s+answer\s+is|it\s+is|it's|that\s+is|that's|"
    r"i\s+think\s+it's|i\s+believe\s+it's|this\s+is)\s+",
    re.IGNORECASE,
)


def normalise_answer(text: str) -> str:
    """SQuAD-style normalisation: lower-case, strip articles, punctuation, spacing."""
    s = text.strip()
    s = _PREAMBLE.sub("", s)
    s = s.lower()
    s = s.translate(_PUNCT)
    s = _ARTICLES.sub(" ", s)
    return _WS.sub(" ", s).strip()


@dataclass(slots=True)
class ClusterResult:
    clusters: list[list[int]]
    """Indices into the input list, one group per meaning."""

    members: list[list[str]]
    """The same grouping, as the original strings."""

    entropy: float
    """Shannon entropy (nats) of the cluster-size distribution."""

    n_clusters: int
    top_mass: float
    """Share of samples in the largest cluster. 1.0 means unanimous."""

    def as_dict(self) -> dict[str, object]:
        return {
            "n_clusters": self.n_clusters,
            "entropy": round(self.entropy, 4),
            "top_mass": round(self.top_mass, 4),
            "members": self.members,
        }


def cluster_answers(
    answers: Sequence[str],
    embed_fn: Callable[[Sequence[str]], list[list[float]]] | None = None,
    *,
    similarity_threshold: float = 0.92,
    entail_fn: Callable[[str, str], bool] | None = None,
    merge_refusals: bool = True,
) -> ClusterResult:
    """Group answers by meaning.

    Strategy, cheapest-first:

    1. **Normalised exact match** - free, and precise for short factual answers.
    2. **Bidirectional entailment** via ``entail_fn`` if supplied. This is the
       definition used in the semantic-entropy papers: two answers share a
       meaning iff each entails the other. Most faithful, most expensive.
    3. **Embedding cosine** via ``embed_fn`` as the fallback for longer answers
       where string matching is too strict.

    With neither ``entail_fn`` nor ``embed_fn`` this degrades to exact-match
    clustering, which is still a usable (if conservative) signal.

    ``similarity_threshold`` defaults to 0.92 rather than the 0.85 used in early
    testing: at 0.85 the clusterer merged distinct short answers, while below
    that it over-split. Tune it with ``halluciwatch tune-threshold``.

    ``merge_refusals`` collapses every "I don't know" onto one cluster. Without
    it a model that honestly declines four times in four different phrasings
    scores as four competing meanings, and its semantic entropy looks like
    disagreement when it is actually consistent, correct behaviour. Observed on
    "who was the 14th person to walk on the Moon?", where llama3.2:3b refused
    every time - correctly noting only 12 people ever did - and still scored
    0.40 because the refusals were worded differently.
    """
    if not answers:
        return ClusterResult([], [], 0.0, 0, 0.0)

    normalised = [normalise_answer(a) for a in answers]

    if merge_refusals:
        from .features.surface import looks_like_refusal

        normalised = [
            _REFUSAL_KEY if looks_like_refusal(original) else norm
            for original, norm in zip(answers, normalised, strict=True)
        ]

    # Pass 1: exact match on the normalised form.
    groups: list[list[int]] = []
    by_norm: dict[str, int] = {}
    for i, norm in enumerate(normalised):
        if norm in by_norm:
            groups[by_norm[norm]].append(i)
        else:
            by_norm[norm] = len(groups)
            groups.append([i])

    # Pass 2: merge remaining distinct groups by meaning.
    if len(groups) > 1 and (entail_fn is not None or embed_fn is not None):
        reps = [g[0] for g in groups]
        vectors: list[list[float]] | None = None
        if entail_fn is None and embed_fn is not None:
            try:
                vectors = embed_fn([answers[i] for i in reps])
            except Exception:
                vectors = None

        merged: list[list[int]] = []
        merged_reps: list[int] = []
        merged_vecs: list[list[float]] = []
        for gi, group in enumerate(groups):
            placed = False
            for mi in range(len(merged)):
                # A refusal never means the same thing as a substantive answer,
                # whatever the embeddings say about their surface similarity.
                if (normalised[reps[gi]] == _REFUSAL_KEY) != (
                    normalised[merged_reps[mi]] == _REFUSAL_KEY
                ):
                    continue
                same = False
                if entail_fn is not None:
                    a, b = answers[reps[gi]], answers[merged_reps[mi]]
                    try:
                        same = entail_fn(a, b) and entail_fn(b, a)
                    except Exception:
                        same = False
                elif vectors is not None:
                    same = _cosine(vectors[gi], merged_vecs[mi]) >= similarity_threshold
                if same:
                    merged[mi].extend(group)
                    placed = True
                    break
            if not placed:
                merged.append(list(group))
                merged_reps.append(reps[gi])
                if vectors is not None:
                    merged_vecs.append(vectors[gi])
        groups = merged

    sizes = [len(g) for g in groups]
    total = sum(sizes)
    entropy = -sum((s / total) * math.log(s / total) for s in sizes if s > 0)

    return ClusterResult(
        clusters=groups,
        members=[[answers[i] for i in g] for g in groups],
        entropy=entropy if entropy > 0.0 else 0.0,
        n_clusters=len(groups),
        top_mass=max(sizes) / total if total else 0.0,
    )


def semantic_entropy(
    answers: Sequence[str],
    embed_fn: Callable[[Sequence[str]], list[list[float]]] | None = None,
    **kwargs: object,
) -> float:
    """Convenience wrapper returning only the entropy value."""
    return cluster_answers(answers, embed_fn, **kwargs).entropy  # type: ignore[arg-type]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)

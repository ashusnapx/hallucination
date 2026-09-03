"""Tests for the signal maths.

These use hand-constructed distributions with known answers rather than random
arrays, so a regression in the entropy or clustering maths actually fails
instead of merely changing a shape.
"""

from __future__ import annotations

import math

import pytest

from halluciwatch.cluster import cluster_answers, normalise_answer
from halluciwatch.features.surface import looks_like_refusal, surface_features
from halluciwatch.features.token import is_content_token, token_features
from halluciwatch.types import Generation, TokenLogprob


def _token(top: list[tuple[str, float]], chosen: int = 0) -> TokenLogprob:
    return TokenLogprob(token=top[chosen][0], logprob=top[chosen][1], top_logprobs=top)


def _gen(tokens: list[TokenLogprob]) -> Generation:
    return Generation(text=" ".join(t.token for t in tokens), model="test", tokens=tokens)


class TestTokenLogprob:
    def test_uniform_distribution_has_max_entropy(self):
        """Four equiprobable options -> ln(4) nats."""
        p = math.log(0.25)
        tok = _token([("a", p), ("b", p), ("c", p), ("d", p)])
        assert tok.entropy() == pytest.approx(math.log(4), abs=1e-6)

    def test_certain_distribution_has_zero_entropy(self):
        tok = _token([("a", math.log(0.9999)), ("b", math.log(0.0001))])
        assert tok.entropy() < 0.01

    def test_margin_is_difference_of_top_two(self):
        tok = _token([("a", math.log(0.6)), ("b", math.log(0.4))])
        assert tok.margin() == pytest.approx(0.2, abs=1e-6)

    def test_margin_without_alternatives_is_zero(self):
        """With top_logprobs=0 there is no distribution to compare against."""
        tok = TokenLogprob(token="a", logprob=math.log(0.5))
        assert tok.margin() == 0.0
        assert tok.entropy() == 0.0

    def test_surprisal_matches_negative_logprob(self):
        tok = TokenLogprob(token="a", logprob=-2.0)
        assert tok.surprisal == 2.0
        assert tok.probability == pytest.approx(math.exp(-2.0))

    def test_distribution_renormalises_truncated_support(self):
        """Ollama returns only top-k, so the mass must be renormalised."""
        tok = _token([("a", math.log(0.3)), ("b", math.log(0.2))])
        dist = tok.distribution()
        assert sum(dist) == pytest.approx(1.0)
        assert dist[0] == pytest.approx(0.6)


class TestTokenFeatures:
    def test_confident_generation_scores_low_entropy_high_margin(self):
        tokens = [_token([("x", math.log(0.98)), ("y", math.log(0.02))]) for _ in range(5)]
        f = token_features(_gen(tokens))
        assert f["tok.mean_entropy"] < 0.15
        assert f["tok.mean_margin"] > 0.9
        assert f["tok.n_tokens"] == 5

    def test_uncertain_generation_scores_high_entropy_low_margin(self):
        p = math.log(0.25)
        tokens = [_token([("a", p), ("b", p), ("c", p), ("d", p)]) for _ in range(5)]
        f = token_features(_gen(tokens))
        assert f["tok.mean_entropy"] > 1.0
        assert f["tok.mean_margin"] < 0.1

    def test_empty_generation_returns_zeros_not_crash(self):
        f = token_features(Generation(text="", model="test", tokens=[]))
        assert set(f.values()) == {0.0}

    def test_perplexity_is_finite_for_extreme_surprisal(self):
        """A pathological token must not produce inf and poison tree splits."""
        tokens = [TokenLogprob(token="z", logprob=-500.0)]
        f = token_features(_gen(tokens))
        assert math.isfinite(f["tok.perplexity"])

    def test_entropy_slope_detects_rising_uncertainty(self):
        low = [("x", math.log(0.99)), ("y", math.log(0.01))]
        high = [("a", math.log(0.25))] * 4
        tokens = [_token(low), _token(low), _token(high), _token(high)]
        assert token_features(_gen(tokens))["tok.entropy_slope"] > 0

    def test_content_entropy_ignores_function_words(self):
        """Uncertainty over 'the' vs 'a' is stylistic, not factual."""
        uncertain = [("the", math.log(0.25)), ("a", math.log(0.25)),
                     ("an", math.log(0.25)), ("of", math.log(0.25))]
        certain = [("Paris", math.log(0.99)), ("Lyon", math.log(0.01))]
        f = token_features(_gen([_token(uncertain), _token(certain)]))
        assert f["tok.mean_content_entropy"] < f["tok.mean_entropy"]


class TestContentTokens:
    @pytest.mark.parametrize("token", ["Paris", "1889", "penicillin"])
    def test_content_words(self, token):
        assert is_content_token(token)

    @pytest.mark.parametrize("token", ["the", " of ", ".", "", "  ", ","])
    def test_function_words_and_punctuation(self, token):
        assert not is_content_token(token)


class TestNormalisation:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("The answer is Paris.", "paris"),
            ("  PARIS  ", "paris"),
            ("It's Paris!", "paris"),
            ("the Eiffel Tower", "eiffel tower"),
        ],
    )
    def test_normalise(self, raw, expected):
        assert normalise_answer(raw) == expected


class TestClustering:
    def test_identical_answers_form_one_cluster_with_zero_entropy(self):
        result = cluster_answers(["Paris", "Paris.", "The answer is Paris"])
        assert result.n_clusters == 1
        assert result.entropy == pytest.approx(0.0)
        assert result.top_mass == 1.0

    def test_all_different_answers_maximise_entropy(self):
        result = cluster_answers(["Paris", "Lyon", "Berlin", "Rome"])
        assert result.n_clusters == 4
        assert result.entropy == pytest.approx(math.log(4), abs=1e-6)

    def test_entropy_is_between_the_extremes_for_a_split(self):
        result = cluster_answers(["Paris", "Paris", "Paris", "Lyon"])
        assert result.n_clusters == 2
        assert result.top_mass == pytest.approx(0.75)
        assert 0 < result.entropy < math.log(2)

    def test_empty_input(self):
        result = cluster_answers([])
        assert result.n_clusters == 0
        assert result.entropy == 0.0

    def test_embedding_failure_falls_back_to_exact_match(self):
        """A broken embedder must degrade, not raise - scoring cannot fail here."""

        def broken(_texts):
            raise RuntimeError("embedding service down")

        result = cluster_answers(["Paris", "Lyon"], broken)
        assert result.n_clusters == 2

    def test_entailment_merges_paraphrases(self):
        def entails(a: str, b: str) -> bool:
            return "paris" in a.lower() and "paris" in b.lower()

        result = cluster_answers(
            ["Paris", "The capital is Paris", "Lyon"], entail_fn=entails
        )
        assert result.n_clusters == 2


class TestRefusalDetection:
    @pytest.mark.parametrize(
        "text",
        [
            "I don't know.",
            "I do not have access to that information.",
            "I'm not aware of any such person.",
            "I cannot provide the exact address.",
            "Sorry, I couldn't find information on that.",
        ],
    )
    def test_detects_refusals(self, text):
        assert looks_like_refusal(text)

    @pytest.mark.parametrize(
        "text",
        ["Paris.", "The capital of France is Paris.", "Marie Curie discovered radium."],
    )
    def test_does_not_flag_real_answers(self, text):
        assert not looks_like_refusal(text)

    def test_refusal_feature_is_set(self):
        assert surface_features("I don't know.")["srf.is_refusal"] == 1.0
        assert surface_features("Paris.")["srf.is_refusal"] == 0.0


class TestSurfaceFeatures:
    def test_counts_words_and_digits(self):
        f = surface_features("The year was 1889 exactly.")
        assert f["srf.n_words"] == 5
        assert f["srf.digit_density"] > 0

    def test_hedges_are_counted(self):
        assert surface_features("It might possibly be Paris.")["srf.hedge_count"] >= 2

    def test_empty_answer_is_safe(self):
        f = surface_features("")
        assert f["srf.n_words"] == 0.0
        assert f["srf.mean_word_len"] == 0.0


class TestRefusalHandling:
    """Refusals are neither hallucinations nor answers, and must be kept apart.

    Both behaviours here were bugs found by running the real system: differently
    worded refusals were counted as competing meanings (inflating semantic
    entropy on honest, consistent behaviour), and the classifier scored honest
    refusals anywhere from 0.27 to 0.60 because refusals are excluded from
    training and it had never seen the feature set.
    """

    def test_differently_worded_refusals_form_one_cluster(self):
        from halluciwatch.cluster import cluster_answers

        result = cluster_answers(
            [
                "I don't have information on the specific order of moonwalkers.",
                "I don't have information on who was the 14th person.",
                "I'm not aware of any such person.",
                "I cannot provide that information.",
            ]
        )
        assert result.n_clusters == 1
        assert result.entropy == 0.0

    def test_refusal_does_not_merge_with_a_real_answer(self):
        from halluciwatch.cluster import cluster_answers

        result = cluster_answers(
            ["I don't have information on that.", "John Young", "John Young"]
        )
        assert result.n_clusters == 2
        sizes = sorted(len(c) for c in result.clusters)
        assert sizes == [1, 2]

    def test_merge_refusals_can_be_disabled(self):
        from halluciwatch.cluster import cluster_answers

        answers = ["I don't know.", "I cannot provide that information."]
        assert cluster_answers(answers, merge_refusals=False).n_clusters == 2
        assert cluster_answers(answers, merge_refusals=True).n_clusters == 1

    def test_entropy_is_never_negative_zero(self):
        """-0.0 formats as "-0.000", which reads as a bug in the UI."""
        from halluciwatch.cluster import cluster_answers

        result = cluster_answers(["Paris", "Paris", "Paris"])
        assert result.entropy == 0.0
        assert f"{result.entropy:.3f}" == "0.000"


class TestPromptConsistency:
    def test_corpus_and_detector_share_one_system_prompt(self):
        """Train/serve skew: features are a property of the prompt that made them.

        This was live in the codebase - the corpus was built with a
        "always give your best guess" prompt while the detector served with a
        "say so plainly rather than guessing" one, so the classifier scored a
        distribution it had never been trained on.
        """
        from halluciwatch.data.build import CorpusConfig
        from halluciwatch.detector import DetectorConfig
        from halluciwatch.types import DEFAULT_SYSTEM_PROMPT

        assert CorpusConfig().system_prompt == DEFAULT_SYSTEM_PROMPT
        assert DetectorConfig().system_prompt == DEFAULT_SYSTEM_PROMPT

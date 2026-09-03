"""Integration tests against a live Ollama server.

Skipped automatically when Ollama is not reachable or the models are not pulled,
so the suite stays green on a machine without them:

    pytest tests/ -m integration        # run only these
    pytest tests/ -m "not integration"  # skip them

These exist because the two most damaging bugs found while building this were
both invisible to unit tests: Ollama returning collapsed embeddings for
capitalised text, and the token-tier cost cliff. Both are properties of the
*live server*, not of our code.
"""

from __future__ import annotations

import pytest

from halluciwatch.backends.ollama import OllamaBackend, OllamaError, OllamaOptions

pytestmark = pytest.mark.integration

GEN_MODEL = "llama3.2:1b"
EMBED_MODEL = "nomic-embed-text"


@pytest.fixture(scope="module")
def backend():
    be = OllamaBackend(model=GEN_MODEL, embed_model=EMBED_MODEL)
    try:
        health = be.health()
    except OllamaError as exc:
        pytest.skip(f"Ollama unavailable: {exc}")
    if not health["generation_model_available"]:
        pytest.skip(f"{GEN_MODEL} not pulled")
    if not health["embed_model_available"]:
        pytest.skip(f"{EMBED_MODEL} not pulled")
    yield be
    be.close()


class TestGeneration:
    def test_returns_text_and_token_logprobs(self, backend):
        gen = backend.generate(
            "What is the capital of France? Answer in one word.",
            options=OllamaOptions(temperature=0.0, seed=42, num_predict=8),
        )
        assert gen.text.strip()
        assert gen.has_logprobs
        assert gen.has_alternatives
        assert gen.eval_tokens > 0
        assert all(t.logprob <= 0 for t in gen.tokens)

    def test_top_logprobs_zero_gives_surprisal_but_no_alternatives(self, backend):
        """The cheap path: chosen-token logprobs only, ~5% overhead."""
        gen = backend.generate(
            "Say hello.", top_logprobs=0, options=OllamaOptions(num_predict=5)
        )
        assert gen.has_logprobs
        assert not gen.has_alternatives
        assert gen.tokens[0].entropy() == 0.0

    def test_rejects_out_of_range_top_logprobs(self, backend):
        """Ollama caps top_logprobs at 20; we fail fast rather than 400."""
        with pytest.raises(ValueError, match="top_logprobs"):
            backend.generate("hi", top_logprobs=50)

    def test_greedy_decoding_is_reproducible(self, backend):
        opts = OllamaOptions(temperature=0.0, seed=7, num_predict=10)
        a = backend.generate("Name a river in Brazil.", options=opts)
        b = backend.generate("Name a river in Brazil.", options=opts)
        assert a.text == b.text

    def test_sampling_produces_variation(self, backend):
        """Semantic entropy needs genuine diversity across seeds."""
        gens = backend.sample(
            "Name any river in the world. One word.",
            n=6,
            temperature=1.0,
            options=OllamaOptions(num_predict=8),
        )
        assert len(gens) == 6
        assert len({g.text.strip().lower() for g in gens}) > 1

    def test_missing_model_gives_actionable_error(self, backend):
        with pytest.raises(OllamaError, match="ollama pull"):
            backend.generate("hi", model="definitely-not-a-real-model:9b")


class TestEmbeddings:
    def test_returns_vectors_of_consistent_dimension(self, backend):
        vectors = backend.embed(["hello world", "goodbye world"])
        assert len(vectors) == 2
        assert len(vectors[0]) == len(vectors[1]) > 0

    def test_lowercasing_prevents_the_unk_collapse(self, backend):
        """Regression test for the bug that silently breaks semantic clustering.

        Ollama does not lower-case input for uncased BERT embedding models, so
        capitalised tokens become [UNK] and unrelated strings collapse onto one
        vector. Measured raw, these two sentences had cosine 1.0000. Our embed()
        lower-cases, which must keep them apart.
        """
        from halluciwatch.backends.ollama import cosine

        a, b = backend.embed(
            ["The capital of France is Paris.", "The capital of Japan is Tokyo."]
        )
        assert cosine(a, b) < 0.95, "different facts must not be near-identical"

    def test_paraphrases_stay_close(self, backend):
        from halluciwatch.backends.ollama import cosine

        a, b = backend.embed(
            ["The capital of France is Paris.", "Paris is the French capital city."]
        )
        assert cosine(a, b) > 0.85

    def test_empty_input_returns_empty(self, backend):
        assert backend.embed([]) == []


class TestDetector:
    def test_scores_a_question_end_to_end(self, backend):
        from halluciwatch.detector import DetectorConfig, HallucinationDetector

        detector = HallucinationDetector(
            backend=backend,
            config=DetectorConfig(model=GEN_MODEL, n_samples=3, max_tokens=32),
        )
        report = detector.score("What is the capital of France?")

        assert 0.0 <= report.risk <= 1.0
        assert report.decision in {"accept", "review", "reject"}
        assert report.answer
        assert report.token_risk
        assert "token" in report.tiers_used
        assert report.fingerprint is not None
        assert len(report.fingerprint) == len(report.fingerprint.names)

    def test_cascade_skips_sampling_when_cheap_signals_are_decisive(self, backend):
        """The cost saving is the whole point; assert it actually happens."""
        from halluciwatch.detector import DetectorConfig, HallucinationDetector

        detector = HallucinationDetector(
            backend=backend,
            config=DetectorConfig(
                model=GEN_MODEL,
                n_samples=3,
                max_tokens=24,
                # An impossible band: nothing should ever escalate.
                escalate_low=1.1,
                escalate_high=1.2,
            ),
        )
        report = detector.score("What is the capital of France?")
        assert "sampling" not in report.tiers_used
        assert any("skipped sampling" in n for n in report.notes)

    def test_force_tiers_overrides_the_cascade(self, backend):
        from halluciwatch.detector import DetectorConfig, HallucinationDetector

        detector = HallucinationDetector(
            backend=backend,
            config=DetectorConfig(model=GEN_MODEL, n_samples=3, max_tokens=24),
        )
        report = detector.score(
            "Who invented the telephone?", force_tiers=["surface", "token", "sampling"]
        )
        assert "sampling" in report.tiers_used
        assert report.clusters

    def test_supplied_answer_skips_generation(self, backend):
        """Ollama cannot return logprobs for text it did not generate."""
        from halluciwatch.detector import DetectorConfig, HallucinationDetector

        detector = HallucinationDetector(
            backend=backend,
            config=DetectorConfig(model=GEN_MODEL, n_samples=0, max_tokens=24),
        )
        report = detector.score("What is 2+2?", answer="The answer is 4.")
        assert report.answer == "The answer is 4."
        assert any("no logprobs" in n for n in report.notes)

"""HTTP API tests with a stubbed detector (no Ollama required).

The regression these exist for: ``ScoreRequest`` must be defined at *module*
scope in ``server.py``. Because that module uses
``from __future__ import annotations``, FastAPI resolves handler annotations
against module globals; a model defined inside ``create_app()`` is a closure
variable, so resolution silently fails, FastAPI treats the body as a query
parameter, and every POST returns 422. That bug is invisible to unit tests of
the detector and to a type-checker - only an actual request catches it.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from halluciwatch.types import Fingerprint, RiskReport  # noqa: E402


class StubDetector:
    """Stands in for HallucinationDetector without touching Ollama."""

    def __init__(self):
        from halluciwatch.detector import DetectorConfig

        self.config = DetectorConfig()
        self.model = None
        self.backend = self
        self.calls: list[dict] = []

    def health(self):
        return {"host": "stub", "version": "0.0.0", "models": []}

    def score(self, question, *, answer=None, force_tiers=None):
        self.calls.append(
            {"question": question, "answer": answer, "force_tiers": force_tiers}
        )
        return RiskReport(
            risk=0.42,
            decision="review",
            answer=answer or "a stub answer",
            question=question,
            model="stub-model",
            tiers_used=["surface", "token"],
            fingerprint=Fingerprint(names=["tok.mean_entropy"], values=[1.5]),
            top_factors=[("tok.mean_entropy", 1.5)],
            token_risk=[("a", 0.1), ("b", 0.9)],
            latency_s=0.01,
        )

    def close(self):
        pass


@pytest.fixture
def client(monkeypatch):
    from halluciwatch import server

    stub = StubDetector()
    app = server.create_app()

    # Replace the detector the lifespan would have loaded.
    async def lifespan_stub(app):
        app.state.detector = stub
        yield

    from contextlib import asynccontextmanager

    app.router.lifespan_context = asynccontextmanager(lifespan_stub)
    with TestClient(app) as c:
        c.stub = stub  # type: ignore[attr-defined]
        yield c


class TestScoreEndpoint:
    def test_accepts_a_json_body(self, client):
        """The 422-on-every-request regression."""
        resp = client.post("/score", json={"question": "What is 2+2?"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["risk"] == 0.42
        assert body["decision"] == "review"
        assert body["question"] == "What is 2+2?"

    def test_passes_optional_fields_through(self, client):
        resp = client.post(
            "/score",
            json={
                "question": "q",
                "answer": "supplied answer",
                "samples": 3,
                "force_tiers": ["token"],
            },
        )
        assert resp.status_code == 200
        call = client.stub.calls[-1]
        assert call["answer"] == "supplied answer"
        assert call["force_tiers"] == ["token"]
        assert client.stub.config.n_samples == 3

    def test_rejects_empty_question(self, client):
        assert client.post("/score", json={"question": ""}).status_code == 422

    def test_rejects_missing_question(self, client):
        assert client.post("/score", json={}).status_code == 422

    def test_rejects_oversized_question(self, client):
        assert client.post("/score", json={"question": "x" * 5000}).status_code == 422

    def test_rejects_out_of_range_samples(self, client):
        assert client.post("/score", json={"question": "q", "samples": 99}).status_code == 422

    def test_response_is_json_serialisable(self, client):
        body = client.post("/score", json={"question": "q"}).json()
        for key in ("risk", "decision", "answer", "tiers_used", "token_risk", "features"):
            assert key in body


class TestOtherEndpoints:
    def test_health(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["calibrated"] is False

    def test_features_documents_the_fingerprint(self, client):
        body = client.get("/features").json()
        assert body["n_features"] > 20
        first = body["features"][0]
        assert {"name", "tier", "description", "higher_is_riskier"} <= set(first)

    def test_stream_emits_sse_events_in_order(self, client):
        resp = client.post("/score/stream", json={"question": "q"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        text = resp.text
        assert text.index("event: status") < text.index("event: answer")
        assert text.index("event: answer") < text.index("event: result")


class TestAbstainDecision:
    """A refusal must not be scored as a hallucination."""

    def test_refusal_yields_abstain_not_reject(self, monkeypatch):
        from halluciwatch.detector import DetectorConfig, HallucinationDetector
        from halluciwatch.types import Generation

        detector = HallucinationDetector.__new__(HallucinationDetector)
        detector.config = DetectorConfig(tiers=("surface", "token"))
        detector.model = None
        detector.feature_names = None

        from halluciwatch.calibration import DecisionPolicy

        # A policy that would call anything above 0.1 a rejection.
        detector.policy = DecisionPolicy(accept_below=0.05, reject_above=0.1)
        monkeypatch.setattr(
            detector,
            "_generate",
            lambda prompt, answer: Generation(
                text="I don't have information on that.", model="stub"
            ),
        )
        report = detector.score("Who was the 14th person on the Moon?")
        assert report.decision == "abstain"
        assert any("declined to answer" in n for n in report.notes)

    def test_substantive_answer_is_still_scored_normally(self, monkeypatch):
        from halluciwatch.calibration import DecisionPolicy
        from halluciwatch.detector import DetectorConfig, HallucinationDetector
        from halluciwatch.types import Generation

        detector = HallucinationDetector.__new__(HallucinationDetector)
        detector.config = DetectorConfig(tiers=("surface", "token"))
        detector.model = None
        detector.feature_names = None
        detector.policy = DecisionPolicy(accept_below=0.05, reject_above=0.1)
        monkeypatch.setattr(
            detector,
            "_generate",
            lambda prompt, answer: Generation(text="On a violin.", model="stub"),
        )
        report = detector.score("Where was the Fiddler?")
        assert report.decision in {"accept", "review", "reject"}

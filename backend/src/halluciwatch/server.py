"""HTTP API.

Two endpoints matter:

``POST /score``
    Generate and score in one call. Returns the risk, the decision, the token
    heat-map and the sampled answers when the cascade escalated.

``POST /score/stream``
    The same thing over server-sent events, emitting the answer first and the
    risk when scoring completes. Scoring can take seconds when the cascade
    escalates, and a UI should be able to show the answer immediately rather
    than blocking on the score.

The detector is loaded once at startup and held on ``app.state``. Ollama calls
are blocking, so every handler dispatches through ``asyncio.to_thread`` to keep
the event loop free.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

log = logging.getLogger(__name__)

__all__ = ["ScoreRequest", "create_app"]


# The request model MUST live at module scope.
#
# This file uses `from __future__ import annotations`, so every annotation is a
# string that FastAPI resolves with typing.get_type_hints() against the handler
# function's *module* globals. A Pydantic model defined inside create_app() is a
# closure variable, not a module global, so resolution fails silently and
# FastAPI falls back to treating the parameter as a query string - every request
# then 422s with "Field required / loc: query". Keeping it here is what makes
# the body parse at all.
try:
    from pydantic import BaseModel, Field

    class ScoreRequest(BaseModel):
        question: str = Field(..., min_length=1, max_length=4000)
        answer: str | None = Field(
            None,
            description=(
                "Score a supplied answer instead of generating one. Token-tier "
                "features are unavailable on this path because Ollama cannot "
                "return logprobs for text it did not generate."
            ),
        )
        samples: int | None = Field(None, ge=0, le=20)
        force_tiers: list[str] | None = None

except ImportError:  # pragma: no cover - server extras not installed
    ScoreRequest = None  # type: ignore[assignment]


def create_app(
    model_dir: str | None = None,
    model: str = "llama3.2:3b",
    host: str = "http://localhost:11434",
    embed_model: str = "nomic-embed-text",
    allow_origins: tuple[str, ...] = ("*",),
) -> Any:
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import StreamingResponse
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "server extras not installed: pip install 'halluciwatch[server]'"
        ) from exc

    from . import __version__
    from .backends.ollama import OllamaError
    from .detector import DetectorConfig, HallucinationDetector


    def _load() -> HallucinationDetector:
        if model_dir:
            return HallucinationDetector.load(model_dir, host=host)
        return HallucinationDetector(
            config=DetectorConfig(model=model, host=host, embed_model=embed_model)
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.detector = _load()
        log.info(
            "detector ready (model=%s, calibrated=%s)",
            app.state.detector.config.model,
            app.state.detector.model is not None,
        )
        try:
            yield
        finally:
            app.state.detector.close()

    app = FastAPI(
        title="HalluciWatch",
        version=__version__,
        summary="Real-time hallucination risk scoring for local LLMs.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allow_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    def _score_sync(payload: ScoreRequest) -> dict[str, Any]:
        detector: HallucinationDetector = app.state.detector
        if payload.samples is not None:
            detector.config.n_samples = payload.samples
        report = detector.score(
            payload.question,
            answer=payload.answer,
            force_tiers=payload.force_tiers,
        )
        return report.to_dict()

    @app.get("/health")
    async def health() -> dict[str, Any]:
        detector: HallucinationDetector = app.state.detector
        try:
            info = await asyncio.to_thread(detector.backend.health)
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {
            "status": "ok",
            "calibrated": detector.model is not None,
            "tiers": list(detector.config.tiers),
            "ollama": info,
        }

    @app.get("/features")
    async def features() -> dict[str, Any]:
        """Document the fingerprint: every feature, its tier and its meaning."""
        from .features import REGISTRY

        return {
            "n_features": len(REGISTRY),
            "features": [
                {
                    "name": s.name,
                    "tier": s.tier,
                    "description": s.description,
                    "higher_is_riskier": s.higher_is_riskier,
                }
                for s in REGISTRY.specs()
            ],
        }

    @app.post("/score")
    async def score(payload: ScoreRequest) -> dict[str, Any]:
        try:
            # Ollama calls are blocking; keep the event loop free.
            return await asyncio.to_thread(_score_sync, payload)
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/score/stream")
    async def score_stream(payload: ScoreRequest) -> StreamingResponse:
        async def events() -> AsyncIterator[str]:
            yield _sse("status", {"stage": "generating"})
            try:
                result = await asyncio.to_thread(_score_sync, payload)
            except OllamaError as exc:
                yield _sse("error", {"detail": str(exc)})
                return
            yield _sse("answer", {"answer": result["answer"]})
            yield _sse("result", result)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

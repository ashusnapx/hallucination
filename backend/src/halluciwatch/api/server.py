"""FastAPI server — returns the full, auditable pipeline breakdown."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScoreRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    response: Optional[str] = Field(default=None, max_length=20000)


class ScoreResponse(BaseModel):
    risk_score: float
    risk_label: str
    confidence: float
    total_latency_ms: float
    response: str
    question: str
    factual_claims: list
    claim_verdicts: list
    claim_details: list = []
    verification_notes: str
    model_used: str
    calculation: Optional[dict] = None
    mermaid: str = ""
    steps: list = []
    degraded: bool = False
    error: Optional[str] = None


def create_app():
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
    except ImportError as exc:  # pragma: no cover
        raise ImportError("pip install fastapi uvicorn") from exc

    from halluciwatch.gemini_client import MODEL_CHAIN, QuotaExhausted, score_question

    app = FastAPI(title="HalluciWatch API", version="0.2.0")

    allowed = os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in allowed if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
            "models": MODEL_CHAIN,
        }

    @app.post("/score", response_model=ScoreResponse)
    async def score(request: ScoreRequest):
        """Score a question. Never raises — failures come back as structured JSON."""
        try:
            result = score_question(question=request.question, response=request.response)
            return ScoreResponse(**vars(result))

        except QuotaExhausted as exc:
            logger.warning("Gemini quota exhausted: %s", exc)
            return JSONResponse(status_code=429, content=_error_payload(request, str(exc)))

        except ValueError as exc:
            return JSONResponse(status_code=400, content=_error_payload(request, str(exc)))

        except Exception as exc:  # noqa: BLE001 - last line of defence
            logger.exception("Unhandled error while scoring")
            return JSONResponse(
                status_code=500,
                content=_error_payload(request, f"{type(exc).__name__}: {exc}"),
            )

    def _error_payload(request: ScoreRequest, message: str) -> dict[str, Any]:
        return ScoreResponse(
            risk_score=0.0,
            risk_label="unavailable",
            confidence=0.0,
            total_latency_ms=0.0,
            response="",
            question=request.question,
            factual_claims=[],
            claim_verdicts=[],
            claim_details=[],
            verification_notes=message,
            model_used="",
            calculation=None,
            mermaid="",
            steps=[],
            degraded=True,
            error=message,
        ).model_dump()

    return app

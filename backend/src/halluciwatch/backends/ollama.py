"""Ollama backend - the reference (and default) backend for HalluciWatch.

Everything in this module was verified empirically against Ollama 0.13.4 on
macOS/arm64. The non-obvious behaviours it works around are documented inline
because they are not in Ollama's docs and they silently corrupt results.
"""

from __future__ import annotations

import json
import logging
import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from ..types import Generation, TokenLogprob

log = logging.getLogger(__name__)

__all__ = ["OllamaBackend", "OllamaError", "OllamaOptions"]

DEFAULT_HOST = "http://localhost:11434"

# Ollama rejects top_logprobs outside 0..20 with a 400.
MAX_TOP_LOGPROBS = 20

# Measured on Apple M1 / llama3.2:1b / 60 generated tokens, median of 5 runs:
#
#   no logprobs               1.710 s   (baseline)
#   logprobs, top_logprobs=0  1.799 s   (+5.2%)
#   top_logprobs=1            3.030 s   (+77.2%)
#   top_logprobs=5            3.103 s   (+81.4%)
#   top_logprobs=20           3.091 s   (+80.7%)
#
# The penalty for asking for *any* alternatives is essentially fixed - it does
# not scale with k. So there is never a reason to ask for k between 1 and 19:
# if you are paying for alternatives at all, take the maximum.
CHEAP_TOP_LOGPROBS = 0
RICH_TOP_LOGPROBS = MAX_TOP_LOGPROBS


class OllamaError(RuntimeError):
    """Raised when Ollama is unreachable, missing a model, or returns an error."""


@dataclass(slots=True)
class OllamaOptions:
    """Sampling options passed through to Ollama's ``options`` object."""

    temperature: float = 0.0
    top_p: float = 0.95
    top_k: int | None = None
    seed: int | None = None
    num_predict: int = 128
    num_ctx: int | None = None
    repeat_penalty: float | None = None
    stop: list[str] | None = None

    def to_payload(self) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "num_predict": self.num_predict,
        }
        if self.top_k is not None:
            opts["top_k"] = self.top_k
        if self.seed is not None:
            opts["seed"] = self.seed
        if self.num_ctx is not None:
            opts["num_ctx"] = self.num_ctx
        if self.repeat_penalty is not None:
            opts["repeat_penalty"] = self.repeat_penalty
        if self.stop:
            opts["stop"] = self.stop
        return opts


def _parse_logprobs(raw: Sequence[dict[str, Any]] | None) -> list[TokenLogprob]:
    """Convert Ollama's ``logprobs`` array into ``TokenLogprob`` objects.

    Verified response shape (``POST /api/generate``, ``logprobs: true``)::

        "logprobs": [
          {"token": "Paris",
           "logprob": -0.0062,
           "bytes": [80, 97, 114, 105, 115],
           "top_logprobs": [
             {"token": "Paris",  "logprob": -0.0062, "bytes": [...]},
             {"token": "Par",    "logprob": -6.4915, "bytes": [...]}
           ]}
        ]

    ``top_logprobs`` is absent or empty when ``top_logprobs=0`` was
    requested.
    """
    out: list[TokenLogprob] = []
    for entry in raw or []:
        alts = [
            (alt.get("token", ""), float(alt["logprob"]))
            for alt in (entry.get("top_logprobs") or [])
            if alt.get("logprob") is not None
        ]
        out.append(
            TokenLogprob(
                token=entry.get("token", ""),
                logprob=float(entry.get("logprob", 0.0)),
                top_logprobs=alts,
            )
        )
    return out


class OllamaBackend:
    """A thin, well-behaved client over Ollama's native API.

    Uses the *native* ``/api/generate`` and ``/api/chat`` endpoints rather than
    the OpenAI-compatible ``/v1`` shim. Both expose logprobs, but the native API
    also returns timing counters (``eval_duration``, ``prompt_eval_count``) that
    the latency accounting depends on.
    """

    def __init__(
        self,
        model: str = "llama3.2:3b",
        host: str = DEFAULT_HOST,
        embed_model: str = "nomic-embed-text",
        timeout: float = 300.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.embed_model = embed_model
        # A pooled client keeps the connection warm; reconnect cost is otherwise
        # charged to every single scoring call.
        self._client = client or httpx.Client(
            base_url=self.host,
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
        )
        self._owns_client = client is None

    # ---------------------------------------------------------------- plumbing

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = self._client.post(path, json=payload)
        except httpx.ConnectError as exc:
            raise OllamaError(
                f"Cannot reach Ollama at {self.host}. Is it running? Try: ollama serve"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaError(f"Ollama timed out on {path}") from exc

        if resp.status_code != 200:
            detail = resp.text[:400]
            if resp.status_code == 404 and "model" in detail.lower():
                name = payload.get("model")
                raise OllamaError(f"Model {name!r} not found. Try: ollama pull {name}")
            raise OllamaError(f"Ollama returned HTTP {resp.status_code} for {path}: {detail}")

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise OllamaError(f"Ollama returned non-JSON for {path}: {resp.text[:200]}") from exc

        if isinstance(data, dict) and data.get("error"):
            raise OllamaError(f"Ollama error on {path}: {data['error']}")
        return data

    # -------------------------------------------------------------- generation

    def generate(
        self,
        prompt: str,
        *,
        options: OllamaOptions | None = None,
        logprobs: bool = True,
        top_logprobs: int = RICH_TOP_LOGPROBS,
        system: str | None = None,
        model: str | None = None,
    ) -> Generation:
        """Generate a completion and capture per-token signals.

        ``top_logprobs`` should be either ``0`` (cheap: chosen-token logprobs
        only) or ``20`` (rich: full alternatives). Intermediate values cost the
        same as 20 - see ``CHEAP_TOP_LOGPROBS`` above.
        """
        opts = options or OllamaOptions()
        if not 0 <= top_logprobs <= MAX_TOP_LOGPROBS:
            raise ValueError(f"top_logprobs must be in 0..{MAX_TOP_LOGPROBS}, got {top_logprobs}")

        payload: dict[str, Any] = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "options": opts.to_payload(),
        }
        if system:
            payload["system"] = system
        if logprobs:
            # Both fields are TOP-LEVEL on the native API, not inside "options".
            payload["logprobs"] = True
            payload["top_logprobs"] = top_logprobs

        started = time.perf_counter()
        data = self._post("/api/generate", payload)
        wall = time.perf_counter() - started

        return Generation(
            text=data.get("response", ""),
            model=payload["model"],
            tokens=_parse_logprobs(data.get("logprobs")),
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            eval_tokens=int(data.get("eval_count") or 0),
            total_duration_s=wall,
            eval_duration_s=(data.get("eval_duration") or 0) / 1e9,
            seed=opts.seed,
            temperature=opts.temperature,
            finish_reason=data.get("done_reason"),
            raw=data,
        )

    def sample(
        self,
        prompt: str,
        n: int,
        *,
        temperature: float = 1.0,
        base_seed: int = 1000,
        options: OllamaOptions | None = None,
        system: str | None = None,
        model: str | None = None,
    ) -> list[Generation]:
        """Draw ``n`` independent samples for self-consistency signals.

        Ollama has no ``n`` parameter, so this issues ``n`` requests with
        distinct seeds. Seeds are explicit rather than random so a run can be
        reproduced exactly.
        """
        base = options or OllamaOptions()
        out: list[Generation] = []
        for i in range(n):
            opts = OllamaOptions(
                temperature=temperature,
                top_p=base.top_p,
                top_k=base.top_k,
                seed=base_seed + i,
                num_predict=base.num_predict,
                num_ctx=base.num_ctx,
                repeat_penalty=base.repeat_penalty,
                stop=base.stop,
            )
            # Samples only need their text - alternatives would triple the cost
            # of the most expensive tier for no benefit.
            out.append(
                self.generate(
                    prompt,
                    options=opts,
                    logprobs=False,
                    top_logprobs=0,
                    system=system,
                    model=model,
                )
            )
        return out

    # -------------------------------------------------------------- embeddings

    def embed(self, texts: Sequence[str], *, model: str | None = None) -> list[list[float]]:
        """Embed texts for semantic clustering.

        .. warning::

           **Inputs are lower-cased before embedding, and this is load-bearing.**

           ``nomic-embed-text`` (and other BERT-family *uncased* embedding
           models) ship an uncased WordPiece vocabulary, but Ollama 0.13.4 does
           not lower-case input before tokenising. Every capitalised token
           therefore maps to ``[UNK]``, and unrelated strings collapse onto the
           same vector. Measured on Ollama 0.13.4::

               cosine("The capital of France is Paris.",
                      "The capital of Japan is Tokyo.")   = 1.0000  (!)
               cosine("John Logie Baird", "Philo Farnsworth") = 0.9786  (!)

           After lower-casing, the same pairs give 0.7212 and 0.4020, while a
           true paraphrase pair stays at 0.9697. Without this normalisation
           every semantic-consistency feature silently becomes noise, which is
           exactly the failure mode this project exists to detect.
        """
        if not texts:
            return []
        payload = {
            "model": model or self.embed_model,
            "input": [t.lower() for t in texts],
        }
        data = self._post("/api/embed", payload)
        embeddings = data.get("embeddings")
        if not embeddings:
            raise OllamaError(f"No embeddings returned by {payload['model']}")
        return [[float(x) for x in vec] for vec in embeddings]

    # ------------------------------------------------------------ housekeeping

    def list_models(self) -> list[str]:
        try:
            data = self._client.get("/api/tags").json()
        except httpx.HTTPError as exc:
            raise OllamaError(f"Cannot list models at {self.host}: {exc}") from exc
        return [m["name"] for m in data.get("models", [])]

    def health(self) -> dict[str, Any]:
        """Check that the server is up and the configured models are present."""
        try:
            version = self._client.get("/api/version").json().get("version", "unknown")
        except httpx.HTTPError as exc:
            raise OllamaError(
                f"Cannot reach Ollama at {self.host}. Is it running? Try: ollama serve"
            ) from exc
        available = self.list_models()

        def _present(name: str) -> bool:
            # `ollama list` reports "llama3.2:1b"; a bare "llama3.2" should match
            # its :latest tag.
            return any(m == name or m.split(":")[0] == name.split(":")[0] for m in available)

        return {
            "host": self.host,
            "version": version,
            "models": available,
            "generation_model": self.model,
            "generation_model_available": _present(self.model),
            "embed_model": self.embed_model,
            "embed_model_available": _present(self.embed_model),
        }

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> OllamaBackend:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity between two dense vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)

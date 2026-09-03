"""Model backends.

``OllamaBackend`` is the reference implementation and the only one required for
the full pipeline. It is a concrete class rather than a plugin system because
one well-understood backend beats an abstraction over none.
"""

from __future__ import annotations

from .ollama import DEFAULT_HOST, OllamaBackend, OllamaError, OllamaOptions, cosine

__all__ = ["DEFAULT_HOST", "OllamaBackend", "OllamaError", "OllamaOptions", "cosine"]

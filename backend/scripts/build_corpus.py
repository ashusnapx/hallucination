#!/usr/bin/env python
"""Build a labelled fingerprint corpus with a local Ollama model.

Usage::

    python scripts/build_corpus.py --model llama3.2:3b --sources trivia_qa nq_open \
        --limit 250 --samples 5 --out data/corpus/llama3.2-3b.jsonl

Resumable: re-running appends only the questions not already present.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from halluciwatch.backends.ollama import OllamaBackend, OllamaError
from halluciwatch.data import CorpusConfig, build_corpus
from halluciwatch.data.sources import load_questions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="llama3.2:3b")
    parser.add_argument("--embed-model", default="nomic-embed-text")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--sources", nargs="+", default=["trivia_qa"])
    parser.add_argument("--limit", type=int, default=250, help="questions per source")
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=48)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--grader", default="fuzzy", choices=["exact", "fuzzy", "judge"])
    parser.add_argument("--out", required=True)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    # httpx logs every request at INFO; at ~6 requests per question that buries
    # the progress lines completely.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    config = CorpusConfig(
        model=args.model,
        embed_model=args.embed_model,
        host=args.host,
        sources=tuple(args.sources),
        limit_per_source=args.limit,
        n_samples=args.samples,
        max_tokens=args.max_tokens,
        seed=args.seed,
        grader=args.grader,
    )

    backend = OllamaBackend(
        model=config.model, host=config.host, embed_model=config.embed_model
    )
    try:
        health = backend.health()
    except OllamaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not health["generation_model_available"]:
        print(f"error: model {config.model!r} not pulled. Run: ollama pull {config.model}",
              file=sys.stderr)
        return 2
    if not health["embed_model_available"]:
        print(f"error: embed model {config.embed_model!r} not pulled. "
              f"Run: ollama pull {config.embed_model}", file=sys.stderr)
        return 2

    questions = []
    for source in config.sources:
        got = load_questions(source, limit=config.limit_per_source, shuffle_seed=config.seed)
        print(f"loaded {len(got)} questions from {source}")
        questions.extend(got)

    started = time.perf_counter()
    stats = {"n": 0, "halluc": 0, "refusal": 0}

    def progress(index: int, total: int, row: dict) -> None:
        stats["n"] += 1
        stats["halluc"] += row["label"]
        stats["refusal"] += bool(row["verdict"]["is_refusal"])
        if stats["n"] % 10 == 0 or index == total:
            elapsed = time.perf_counter() - started
            rate = elapsed / max(stats["n"], 1)
            remaining = (total - index) * rate
            print(
                f"[{index}/{total}] {rate:.1f}s/q  "
                f"halluc={stats['halluc'] / stats['n']:.0%}  "
                f"refusal={stats['refusal'] / stats['n']:.0%}  "
                f"eta={remaining / 60:.0f}m",
                flush=True,
            )

    build_corpus(
        config,
        args.out,
        backend=backend,
        questions=questions,
        progress=progress,
        resume=not args.no_resume,
    )
    print(f"done in {(time.perf_counter() - started) / 60:.1f} min -> {args.out}")
    backend.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line interface.

    halluciwatch doctor                       check Ollama and models
    halluciwatch build   --limit 300 ...      generate a labelled corpus
    halluciwatch train   --corpus ...         fit and calibrate the detector
    halluciwatch ablate  --corpus ...         measure what each tier buys
    halluciwatch refresh --corpus ...         recompute features, no regeneration
    halluciwatch score   "question"           score one question
    halluciwatch serve                        run the HTTP API

Written with argparse rather than a CLI framework so the package has no
dependency beyond the standard library for its entry point.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import __version__

# ANSI colours, disabled when stdout is not a terminal.
_TTY = sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def _green(t: str) -> str:
    return _c(t, "32")


def _yellow(t: str) -> str:
    return _c(t, "33")


def _red(t: str) -> str:
    return _c(t, "31")


def _dim(t: str) -> str:
    return _c(t, "2")


def _bold(t: str) -> str:
    return _c(t, "1")


def _risk_colour(risk: float, decision: str) -> str:
    text = f"{risk:.3f} ({decision})"
    if decision == "accept":
        return _green(text)
    if decision == "reject":
        return _red(text)
    if decision == "abstain":
        return _dim(text)
    return _yellow(text)


def _bar(value: float, width: int = 28) -> str:
    filled = round(min(max(value, 0.0), 1.0) * width)
    return "█" * filled + "░" * (width - filled)


# --------------------------------------------------------------------- doctor


def cmd_doctor(args: argparse.Namespace) -> int:
    from .backends.ollama import OllamaBackend, OllamaError

    backend = OllamaBackend(model=args.model, host=args.host, embed_model=args.embed_model)
    try:
        health = backend.health()
    except OllamaError as exc:
        print(_red(f"✗ {exc}"))
        return 2

    print(f"{_green('✓')} Ollama {health['version']} at {health['host']}")

    ok = True
    for label, key, name in (
        ("generation model", "generation_model_available", health["generation_model"]),
        ("embedding model", "embed_model_available", health["embed_model"]),
    ):
        if health[key]:
            print(f"{_green('✓')} {label}: {name}")
        else:
            print(f"{_red('✗')} {label}: {name} not pulled -> ollama pull {name}")
            ok = False

    if health["models"]:
        print(_dim(f"  available: {', '.join(health['models'])}"))

    if ok:
        try:
            gen = backend.generate(
                "Say OK.", logprobs=True, top_logprobs=20,
            )
            has = "yes" if gen.has_alternatives else "no"
            print(f"{_green('✓')} logprobs with top-k alternatives: {has} "
                  f"({len(gen.tokens)} tokens)")
            vectors = backend.embed(["hello", "goodbye"])
            print(f"{_green('✓')} embeddings: dim={len(vectors[0])}")
        except OllamaError as exc:
            print(_red(f"✗ smoke test failed: {exc}"))
            ok = False

    backend.close()
    return 0 if ok else 2


# ---------------------------------------------------------------------- build


def cmd_build(args: argparse.Namespace) -> int:
    from .backends.ollama import OllamaBackend, OllamaError
    from .data import CorpusConfig, build_corpus
    from .data.sources import load_questions

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

    questions = []
    for source in config.sources:
        got = load_questions(source, limit=config.limit_per_source, shuffle_seed=config.seed)
        print(f"loaded {len(got):>4} questions from {source}")
        questions.extend(got)

    backend = OllamaBackend(model=config.model, host=config.host, embed_model=config.embed_model)
    stats = {"n": 0, "halluc": 0, "refusal": 0}

    def progress(index: int, total: int, row: dict[str, Any]) -> None:
        stats["n"] += 1
        stats["halluc"] += row["label"]
        stats["refusal"] += bool(row["verdict"]["is_refusal"])
        if stats["n"] % 10 == 0 or index == total:
            print(
                f"  [{index:>4}/{total}] halluc={stats['halluc'] / stats['n']:>3.0%} "
                f"refusal={stats['refusal'] / stats['n']:>3.0%}",
                flush=True,
            )

    try:
        path = build_corpus(
            config, args.out, backend=backend, questions=questions,
            progress=progress, resume=not args.no_resume,
        )
    except OllamaError as exc:
        print(_red(f"✗ {exc}"), file=sys.stderr)
        return 2
    finally:
        backend.close()

    print(f"{_green('✓')} corpus -> {path}")
    return 0


# ---------------------------------------------------------------------- train


def cmd_train(args: argparse.Namespace) -> int:
    from .data.build import corpus_to_matrix, load_corpus
    from .features import REGISTRY
    from .model import save_detector, train_classifier
    from .types import DEFAULT_SYSTEM_PROMPT

    rows = load_corpus(args.corpus)
    if not rows:
        print(_red(f"✗ no rows in {args.corpus}"), file=sys.stderr)
        return 2

    tiers = tuple(args.tiers)
    names = REGISTRY.names(tiers)
    X, y, groups, kept = corpus_to_matrix(rows, names)

    if len(y) == 0:
        print(_red("✗ no usable rows after dropping refusals"), file=sys.stderr)
        return 2

    print(f"corpus: {len(rows)} rows, {len(kept)} usable "
          f"({len(rows) - len(kept)} refusals dropped)")
    print(f"labels: {int(y.sum())} hallucinated / {len(y)} ({y.mean():.1%} base rate)")
    print(f"features: {len(names)} across tiers {'+'.join(tiers)}")

    detector = train_classifier(
        X, y, names, groups=groups, tiers=REGISTRY.tiers_for(names),
        kind=args.estimator, seed=args.seed, n_splits=args.folds,
        target_error=args.target_error,
        config={
            "model": rows[0].get("model", args.model_name),
            "tiers": list(tiers),
            "corpus": str(args.corpus),
            "n_rows": len(kept),
            # Recorded so load_detector can detect train/serve prompt skew.
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
        },
    )

    m = detector.metrics
    print()
    print(_bold("cross-validated performance (grouped by question)"))
    print(f"  AUROC   {m['auroc']:.3f}      AUPRC  {m['auprc']:.3f}")
    print(f"  F1@0.5  {m['f1_at_0.5']:.3f}      Brier  {m['brier']:.3f}   ECE {m['ece']:.3f}")
    print(f"  AURC    {m['aurc']:.3f}  (lower is better)")

    # A single coverage number at one target hides the shape of the trade-off,
    # and reads as a failure when the target is simply unreachable on this data.
    frontier = m.get("coverage_frontier") or {}
    if frontier:
        print()
        print(_bold("selective prediction — how much can be auto-accepted"))
        print(f"  {'target error':<14} {'coverage':>9}")
        for target, coverage in sorted(frontier.items(), key=lambda kv: float(kv[0])):
            note = "" if float(coverage) > 0 else _dim("   (unreachable on this data)")
            print(f"  {float(target):>12.0%} {float(coverage):>9.1%}{note}")
        print(_dim(f"  base rate is {m['base_rate']:.1%}; accepting everything inherits that"))

    if detector.per_tier_metrics:
        print()
        print(_bold("per-tier AUROC (each family alone)"))
        for tier, tm in sorted(
            detector.per_tier_metrics.items(), key=lambda kv: -kv[1]["auroc"]
        ):
            print(f"  {tier:<10} {tm['auroc']:.3f}  ({tm['n_features']} features)")

    print()
    print(_bold("top features by gain"))
    for name, importance in detector.importances[:8]:
        print(f"  {name:<28} {importance:.4f}")

    out = save_detector(detector, args.out)
    print()
    print(f"{_green('✓')} saved -> {out}")
    return 0


# --------------------------------------------------------------------- ablate


def cmd_ablate(args: argparse.Namespace) -> int:
    from .data.build import load_corpus
    from .evaluation.ablation import format_ablation, run_ablation, single_feature_auroc

    rows = load_corpus(args.corpus)
    if not rows:
        print(_red(f"✗ no rows in {args.corpus}"), file=sys.stderr)
        return 2

    results = run_ablation(
        rows, tiers=tuple(args.tiers), kind=args.estimator,
        seed=args.seed, n_splits=args.folds, n_samples=args.samples,
    )
    print(_bold("signal-family ablation"))
    print(format_ablation(results))

    print()
    print(_bold("strongest individual features"))
    for name, auroc in single_feature_auroc(rows, top_k=10):
        print(f"  {name:<28} {auroc:.3f}  {_dim(_bar(auroc))}")

    if args.json:
        Path(args.json).write_text(
            json.dumps([r.to_dict() for r in results], indent=2)
        )
        print(f"\n{_green('✓')} wrote {args.json}")
    return 0


# -------------------------------------------------------------------- refresh


def cmd_refresh(args: argparse.Namespace) -> int:
    """Recompute sampling features from stored samples, without regenerating."""
    from .backends.ollama import OllamaBackend, OllamaError
    from .data.build import load_corpus, refresh_consistency_features

    rows = load_corpus(args.corpus)
    if not rows:
        print(_red(f"✗ no rows in {args.corpus}"), file=sys.stderr)
        return 2

    backend = OllamaBackend(model=args.model, host=args.host, embed_model=args.embed_model)
    try:
        updated = refresh_consistency_features(
            rows, backend, similarity_threshold=args.similarity_threshold
        )
    except OllamaError as exc:
        print(_red(f"✗ {exc}"), file=sys.stderr)
        return 2
    finally:
        backend.close()

    out = Path(args.out or args.corpus)
    with out.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

    print(f"{_green('✓')} refreshed {updated}/{len(rows)} rows -> {out}")
    return 0


# ---------------------------------------------------------------------- score


def cmd_score(args: argparse.Namespace) -> int:
    from .backends.ollama import OllamaError
    from .detector import DetectorConfig, HallucinationDetector

    try:
        if args.model_dir:
            detector = HallucinationDetector.load(args.model_dir, host=args.host)
        else:
            detector = HallucinationDetector(
                config=DetectorConfig(
                    model=args.model, host=args.host, embed_model=args.embed_model,
                    n_samples=args.samples, max_tokens=args.max_tokens,
                )
            )
    except FileNotFoundError:
        print(_red(f"✗ no detector at {args.model_dir}"), file=sys.stderr)
        return 2

    try:
        for question in args.question:
            report = detector.score(question)
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
                continue

            print()
            print(_bold(f"Q  {question}"))
            print(f"A  {report.answer}")
            print()
            print(f"   risk    {_bar(report.risk)}  {_risk_colour(report.risk, report.decision)}")
            if not report.calibrated:
                print(_dim("           heuristic score - train a detector for a calibrated one"))
            print(_dim(f"   tiers   {'+'.join(report.tiers_used)}   "
                       f"latency {report.latency_s:.2f}s (overhead {report.overhead_s:.2f}s)"))
            if report.top_factors:
                factors = "  ".join(f"{n.split('.')[-1]}={v:.3f}" for n, v in report.top_factors)
                print(_dim(f"   signals {factors}"))
            if report.clusters and len(report.clusters) > 1:
                print(_dim(f"   the model gave {len(report.clusters)} different answers:"))
                for cluster in report.clusters[:4]:
                    print(_dim(f"     - {cluster[0][:66]} (x{len(cluster)})"))
            for note in report.notes:
                print(_dim(f"   note    {note}"))
    except OllamaError as exc:
        print(_red(f"✗ {exc}"), file=sys.stderr)
        return 2
    finally:
        detector.close()
    return 0


# ---------------------------------------------------------------------- serve


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print(_red("✗ server extras not installed: pip install 'halluciwatch[server]'"),
              file=sys.stderr)
        return 2

    from .server import create_app

    app = create_app(
        model_dir=args.model_dir, model=args.model, host=args.host,
        embed_model=args.embed_model,
    )
    uvicorn.run(app, host=args.bind, port=args.port, log_level="info")
    return 0


# ------------------------------------------------------------------------ cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="halluciwatch",
        description="Real-time hallucination risk scoring for local LLMs.",
    )
    parser.add_argument("--version", action="version", version=f"halluciwatch {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--model", default="llama3.2:3b")
        p.add_argument("--embed-model", default="nomic-embed-text")
        p.add_argument("--host", default="http://localhost:11434")

    p = sub.add_parser("doctor", help="check Ollama connectivity and models")
    common(p)
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("build", help="generate a labelled fingerprint corpus")
    common(p)
    p.add_argument("--sources", nargs="+", default=["trivia_qa"])
    p.add_argument("--limit", type=int, default=250, help="questions per source")
    p.add_argument("--samples", type=int, default=5)
    p.add_argument("--max-tokens", type=int, default=48)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--grader", default="fuzzy", choices=["exact", "fuzzy", "judge"])
    p.add_argument("--out", required=True)
    p.add_argument("--no-resume", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("train", help="train and calibrate the risk classifier")
    p.add_argument("--corpus", required=True)
    p.add_argument("--out", default="models/detector")
    p.add_argument("--tiers", nargs="+", default=["surface", "token", "sampling"])
    p.add_argument("--estimator", default="xgboost",
                   choices=["xgboost", "lightgbm", "sklearn"])
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--target-error", type=float, default=0.10)
    p.add_argument("--model-name", default="unknown")
    p.set_defaults(func=cmd_train)

    p = sub.add_parser("ablate", help="measure what each signal tier buys")
    p.add_argument("--corpus", required=True)
    p.add_argument("--tiers", nargs="+", default=["surface", "token", "sampling"])
    p.add_argument("--estimator", default="xgboost",
                   choices=["xgboost", "lightgbm", "sklearn"])
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--samples", type=int, default=6)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--json", help="also write results to this path")
    p.set_defaults(func=cmd_ablate)

    p = sub.add_parser(
        "refresh",
        help="recompute sampling features from stored samples (no regeneration)",
    )
    p.add_argument("--corpus", required=True)
    p.add_argument("--out", help="defaults to overwriting --corpus")
    p.add_argument("--model", default="llama3.2:3b")
    p.add_argument("--embed-model", default="nomic-embed-text")
    p.add_argument("--host", default="http://localhost:11434")
    p.add_argument("--similarity-threshold", type=float, default=0.92)
    p.set_defaults(func=cmd_refresh)

    p = sub.add_parser("score", help="score one or more questions")
    common(p)
    p.add_argument("question", nargs="+")
    p.add_argument("--model-dir", help="trained detector directory")
    p.add_argument("--samples", type=int, default=6)
    p.add_argument("--max-tokens", type=int, default=128)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("serve", help="run the HTTP API")
    common(p)
    p.add_argument("--model-dir")
    p.add_argument("--bind", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

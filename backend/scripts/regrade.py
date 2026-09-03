#!/usr/bin/env python
"""Re-grade a corpus with the model-judge, without regenerating anything.

Why this exists
---------------
The corpus was first labelled by string matching: normalised exact match, then
token-F1 against the gold aliases. That is cheap and precise, but it is *too
strict* on paraphrase, and every positive label in the corpus came from its
fuzzy path. Spot-checking found real mislabels:

    "Where would you find myoglobin?"
        model "Muscle cells (skeletal and cardiac)" vs gold "Muscle tissue"
    "Warren Beatty's first movie?"
        model "Splendour" vs gold "Splendor in the Grass"

Both were labelled hallucinations. Label noise of this kind puts a hard ceiling
on achievable AUROC, because the detector is penalised for correctly scoring an
answer that was in fact right.

This pass keeps every string-match agreement and only asks the judge about rows
the matcher called *wrong* — those are where the false-negative risk lives, and
it keeps the judge's own bias from manufacturing new positives. The judge must
clear a confidence bar or the original label stands.

Answers are not regenerated, so features and samples are untouched: only
``label`` and ``verdict`` change.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from halluciwatch.backends.ollama import OllamaBackend, OllamaError
from halluciwatch.data.grading import _judge


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", help="defaults to overwriting --corpus")
    ap.add_argument("--model", default="llama3.2:3b")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument(
        "--min-confidence",
        type=float,
        default=0.75,
        help="judge must be this sure to overturn a string-match verdict",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = [json.loads(line) for line in Path(args.corpus).read_text().splitlines() if line.strip()]
    backend = OllamaBackend(model=args.model, host=args.host)

    flipped: list[dict] = []
    stats: Counter[str] = Counter()

    try:
        for i, row in enumerate(rows, 1):
            verdict = row.get("verdict", {})
            if verdict.get("is_refusal"):
                stats["skipped_refusal"] += 1
                continue
            # Only revisit rows the matcher called wrong. An agreement between
            # exact-match and the judge tells us nothing new, and asking the
            # judge about correct answers only invites it to invent errors.
            if row.get("label") != 1:
                stats["kept_correct"] += 1
                continue

            try:
                result = _judge(
                    backend,
                    row["question"],
                    row["answer"],
                    row.get("gold", []),
                    args.min_confidence,
                )
            except OllamaError as exc:
                print(f"  judge failed on row {i}: {exc}", file=sys.stderr)
                result = None

            if result is None:
                stats["judge_unsure_kept"] += 1
                continue

            is_correct, confidence = result
            if is_correct:
                stats["flipped_to_correct"] += 1
                flipped.append(
                    {
                        "question": row["question"],
                        "answer": row["answer"],
                        "gold": row.get("gold", [])[:2],
                        "confidence": round(confidence, 3),
                    }
                )
                row["label"] = 0
                row["verdict"] = {
                    **verdict,
                    "correct": True,
                    "strategy": "judge",
                    "confidence": round(confidence, 3),
                }
            else:
                stats["judge_agreed_wrong"] += 1

            if i % 50 == 0:
                print(f"  [{i}/{len(rows)}] flipped={stats['flipped_to_correct']}", flush=True)
    finally:
        backend.close()

    usable = [r for r in rows if not r.get("verdict", {}).get("is_refusal")]
    new_rate = sum(r["label"] for r in usable) / max(len(usable), 1)

    print("\nre-grading summary")
    for k, v in sorted(stats.items()):
        print(f"  {k:<22} {v}")
    print(f"  new base rate          {new_rate:.3f}")

    if flipped:
        print(f"\n{min(len(flipped), 12)} of {len(flipped)} labels the judge overturned:")
        for f in flipped[:12]:
            print(f"  Q  {f['question'][:66]}")
            print(f"     model {f['answer'][:56]!r}  gold {f['gold']}  conf {f['confidence']}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    out = Path(args.out or args.corpus)
    with out.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

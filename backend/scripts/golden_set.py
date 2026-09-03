#!/usr/bin/env python
"""Build a golden evaluation set by dual-grading the corpus.

What a golden set is for
------------------------
Every metric this project reports is only as good as the labels underneath it.
The corpus was labelled by string matching against gold aliases, which is
precise but too strict on paraphrase — spot-checking found answers like
"Muscle cells" (gold: "Muscle tissue") labelled as hallucinations. Label noise
puts a hard ceiling on achievable AUROC, because the detector gets penalised for
correctly scoring an answer that was in fact right.

The method here is standard inter-rater practice:

1. Grade every answer twice, by two *independent* raters — the string matcher
   and a larger judge model that did not generate the answer.
2. Where they **agree**, treat the label as verified. Two independent methods
   reaching the same verdict is strong evidence.
3. Where they **disagree**, the item is *contested*. Contested items are written
   out in full so a human can adjudicate them rather than being silently
   resolved by whichever rater we happened to trust.
4. Report Cohen's kappa, so the reliability of the labelling is itself a
   measured number rather than an assumption.

The judge must be a **different and larger** model than the generator. Judging
your own output shares its blind spots: at 3B the judge agreed with the string
matcher on 239 of 264 items and overturned none, including the ones that were
demonstrably mislabelled.

Answers are never regenerated; only labels are re-examined.
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


def cohens_kappa(a: list[int], b: list[int]) -> float:
    """Agreement between two raters, corrected for agreement by chance."""
    n = len(a)
    if n == 0:
        return 0.0
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    # Expected agreement if both raters kept their marginals but chose at random.
    pa1, pb1 = sum(a) / n, sum(b) / n
    expected = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if expected >= 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True, help="golden set (verified rows only)")
    ap.add_argument("--contested-out", help="rows the two raters disagreed on")
    ap.add_argument("--judge-model", default="qwen2.5:7b-instruct")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--limit", type=int, default=0, help="0 = whole corpus")
    args = ap.parse_args()

    rows = [
        json.loads(line)
        for line in Path(args.corpus).read_text().splitlines()
        if line.strip()
    ]
    rows = [r for r in rows if not r.get("verdict", {}).get("is_refusal")]
    if args.limit:
        rows = rows[: args.limit]

    backend = OllamaBackend(model=args.judge_model, host=args.host)

    string_labels: list[int] = []
    judge_labels: list[int] = []
    golden: list[dict] = []
    contested: list[dict] = []
    unsure = 0

    try:
        for i, row in enumerate(rows, 1):
            string_label = int(row["label"])  # 1 = hallucinated

            try:
                # min_confidence=0 so the judge always commits; disagreement is
                # the signal we want, not abstention.
                result = _judge(
                    backend, row["question"], row["answer"], row.get("gold", []), 0.0
                )
            except OllamaError as exc:
                print(f"  judge failed on row {i}: {exc}", file=sys.stderr)
                result = None

            if result is None:
                unsure += 1
                continue

            judge_correct, confidence = result
            judge_label = 0 if judge_correct else 1

            string_labels.append(string_label)
            judge_labels.append(judge_label)

            record = {
                **row,
                "golden": {
                    "string_label": string_label,
                    "judge_label": judge_label,
                    "judge_confidence": round(confidence, 3),
                    "judge_model": args.judge_model,
                },
            }

            if string_label == judge_label:
                record["label"] = string_label
                record["golden"]["status"] = "verified"
                golden.append(record)
            else:
                record["golden"]["status"] = "contested"
                contested.append(record)

            if i % 50 == 0:
                print(
                    f"  [{i}/{len(rows)}] verified={len(golden)} contested={len(contested)}",
                    flush=True,
                )
    finally:
        backend.close()

    kappa = cohens_kappa(string_labels, judge_labels)
    n_rated = len(string_labels)
    agreement = sum(a == b for a, b in zip(string_labels, judge_labels, strict=True))

    print("\ngolden set summary")
    print(f"  rated                  {n_rated}")
    print(f"  judge unsure (dropped) {unsure}")
    print(f"  verified (agreed)      {len(golden)}  ({len(golden) / max(n_rated, 1):.1%})")
    print(f"  contested (disagreed)  {len(contested)}  ({len(contested) / max(n_rated, 1):.1%})")
    print(f"  Cohen's kappa          {kappa:.3f}  {_kappa_reading(kappa)}")
    if golden:
        rate = sum(r["label"] for r in golden) / len(golden)
        print(f"  golden base rate       {rate:.3f}")

    # Which direction do the raters disagree in? A one-sided split says the
    # string matcher is systematically strict (or the judge systematically soft).
    direction = Counter(
        "string=halluc, judge=correct" if r["golden"]["string_label"] == 1 else
        "string=correct, judge=halluc"
        for r in contested
    )
    if direction:
        print("\n  disagreement direction")
        for k, v in direction.most_common():
            print(f"    {k:<32} {v}")

    if contested:
        print(f"\n  {min(len(contested), 10)} of {len(contested)} contested items:")
        for r in contested[:10]:
            g = r["golden"]
            who = "string says hallucinated" if g["string_label"] == 1 else "string says correct"
            print(f"    Q  {r['question'][:64]}")
            print(
                f"       model {r['answer'][:48]!r}  gold {r.get('gold', [])[:2]}"
            )
            print(f"       {who}, judge disagrees (conf {g['judge_confidence']})")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for r in golden:
            fh.write(json.dumps(r) + "\n")
    print(f"\nwrote {out}  ({len(golden)} verified rows)")

    if args.contested_out and contested:
        cp = Path(args.contested_out)
        with cp.open("w") as fh:
            for r in contested:
                fh.write(json.dumps(r) + "\n")
        print(f"wrote {cp}  ({len(contested)} contested rows for human review)")

    stats = {
        "judge_model": args.judge_model,
        "n_rated": n_rated,
        "n_verified": len(golden),
        "n_contested": len(contested),
        "n_judge_unsure": unsure,
        "cohens_kappa": round(kappa, 4),
        "raw_agreement": round(agreement / max(n_rated, 1), 4),
        "golden_base_rate": round(
            sum(r["label"] for r in golden) / max(len(golden), 1), 4
        ),
        "disagreement_direction": dict(direction),
    }
    Path(str(out) + ".stats.json").write_text(json.dumps(stats, indent=2))
    return 0


def _kappa_reading(k: float) -> str:
    """Landis & Koch (1977) conventional bands."""
    if k < 0.0:
        return "(worse than chance)"
    if k < 0.20:
        return "(slight)"
    if k < 0.40:
        return "(fair)"
    if k < 0.60:
        return "(moderate)"
    if k < 0.80:
        return "(substantial)"
    return "(almost perfect)"


if __name__ == "__main__":
    raise SystemExit(main())

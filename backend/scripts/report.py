#!/usr/bin/env python
"""Generate RESULTS.md from a corpus and a trained detector.

Everything in the report is computed from the artefacts on disk, so the numbers
in the repository cannot drift away from the numbers the code produces.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from halluciwatch.data.build import corpus_to_matrix, load_corpus
from halluciwatch.evaluation.ablation import (
    format_ablation,
    run_ablation,
    single_feature_auroc,
)
from halluciwatch.evaluation.metrics import evaluate, risk_coverage_curve
from halluciwatch.features import REGISTRY


def _corpus_summary(rows: list[dict]) -> str:
    from collections import Counter

    by_source = Counter(r.get("source", "?") for r in rows)
    by_model = Counter(r.get("model", "?") for r in rows)
    refusals = sum(1 for r in rows if r.get("verdict", {}).get("is_refusal"))
    graded = Counter(r.get("verdict", {}).get("strategy", "?") for r in rows)
    labels = [r["label"] for r in rows if not r.get("verdict", {}).get("is_refusal")]

    lines = [
        "| property | value |",
        "| --- | --- |",
        f"| rows generated | {len(rows)} |",
        f"| refusals excluded | {refusals} ({refusals / max(len(rows), 1):.1%}) |",
        f"| rows used for training | {len(labels)} |",
        f"| hallucination base rate | {np.mean(labels):.1%} |" if labels else "| base rate | n/a |",
        f"| models | {', '.join(f'{k} ({v})' for k, v in by_model.items())} |",
        f"| sources | {', '.join(f'{k} ({v})' for k, v in by_source.items())} |",
        f"| grader decisions | {', '.join(f'{k}: {v}' for k, v in graded.most_common())} |",
    ]
    return "\n".join(lines)


def _risk_coverage_table(risks: np.ndarray, labels: np.ndarray) -> str:
    coverage, errors = risk_coverage_curve(risks, labels)
    if len(coverage) == 0:
        return "_no data_"
    lines = ["| auto-accept coverage | error rate among accepted |", "| --- | --- |"]
    for target in (0.2, 0.4, 0.5, 0.6, 0.8, 1.0):
        idx = int(min(target * len(coverage), len(coverage)) - 1)
        if idx >= 0:
            lines.append(f"| {coverage[idx]:.0%} | {errors[idx]:.1%} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", default="RESULTS.md")
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args()

    rows = load_corpus(args.corpus)
    if not rows:
        print(f"error: no rows in {args.corpus}", file=sys.stderr)
        return 2

    meta_path = Path(args.model_dir) / "detector.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    names = meta.get("feature_names") or REGISTRY.names(("surface", "token", "sampling"))
    X, y, groups, _kept = corpus_to_matrix(rows, names)

    # Re-derive out-of-fold predictions so the report's curves match the model's
    # reported metrics rather than being scored in-sample.
    from halluciwatch.calibration import Calibrator
    from halluciwatch.model import _grouped_folds, _make_estimator

    folds = _grouped_folds(groups, 5, 42)
    oof = np.zeros(len(y))
    for tr, te in folds:
        est = _make_estimator("xgboost", 42, int(y[tr].sum()), int((1 - y[tr]).sum()))
        est.fit(X[tr], y[tr])
        oof[te] = est.predict_proba(X[te])[:, 1]

    # Cross-fitted calibration, matching train_classifier exactly. Measuring ECE
    # on scores the calibrator was fitted on would report ~0 regardless of the
    # model's real behaviour.
    honest = np.zeros(len(y))
    for _, te in folds:
        mask = np.ones(len(y), dtype=bool)
        mask[te] = False
        honest[te] = Calibrator(min_samples=50).fit(oof[mask], y[mask]).transform(oof[te])

    # Ranking metrics use the raw scores; isotonic calibration is only weakly
    # monotone, so its plateaus create ties that cost ~0.02 AUROC without
    # changing the model's actual ordering ability. Calibration metrics use the
    # cross-fitted probabilities. This is the same split train_classifier uses.
    full = evaluate(oof, y, bootstrap=1000)
    cal = evaluate(honest, y, bootstrap=0)

    ablation = run_ablation(rows, n_samples=args.samples)
    top_features = single_feature_auroc(rows, top_k=12)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    auroc_cell = f"{full.auroc:.3f} [{full.auroc_ci[0]:.3f}, {full.auroc_ci[1]:.3f}]"
    doc = f"""# Results

Generated {generated} by `scripts/report.py`. Every number is computed from
`{args.corpus}` and `{args.model_dir}`; nothing here is hand-entered.

## Corpus

{_corpus_summary(rows)}

Labels come from normalised exact-match / token-F1 grading against gold answer
aliases. Refusals are excluded rather than labelled, because a refusal is
neither a hallucination nor a correct answer.

## Detector performance

Cross-validated, **grouped by question** so no question appears in both train
and test.

Ranking metrics (AUROC, AUPRC) are computed on raw out-of-fold scores;
calibration metrics (Brier, ECE) on cross-fitted isotonic probabilities, so no
point is ever scored by a calibrator that saw it.

| metric | value | what it means |
| --- | --- | --- |
| AUROC | {auroc_cell} | ranking quality; 0.5 is chance |
| AUPRC | {full.auprc:.3f} | precision-recall area (base rate {full.base_rate:.1%}) |
| F1 @ 0.5 | {cal.f1:.3f} | at the default probability threshold |
| Brier | {cal.brier:.3f} | squared error of the calibrated probability |
| ECE | {cal.ece:.3f} | calibration gap after cross-fitted isotonic; lower is better |
| AURC | {cal.aurc:.3f} | area under risk-coverage; lower is better |

The 95% interval is a percentile bootstrap over {full.n} rows. With a corpus
this size the interval is wide enough that small differences between
configurations are not meaningful.

## Risk-coverage

If you auto-accept the answers the detector considers safest, this is the error
rate you inherit:

{_risk_coverage_table(honest, y)}

## What each signal tier buys

```
{format_ablation(ablation)}
```

Cost is the measured marginal latency per query on an Apple M1
(`top_logprobs` penalty for the token tier, one generation per sample for the
sampling tier).

## Strongest individual features

| feature | AUROC alone | tier |
| --- | --- | --- |
"""
    tier_of = {s.name: s.tier for s in REGISTRY.specs()}
    for name, auroc in top_features:
        doc += f"| `{name}` | {auroc:.3f} | {tier_of.get(name, '?')} |\n"

    doc += """
A single feature scoring close to the full model is a useful warning: it means
the ensemble is adding little, and the cheap path is most of the value.

## Feature importances (trained model)

| feature | gain |
| --- | --- |
"""
    for name, gain in meta.get("importances", [])[:12]:
        doc += f"| `{name}` | {gain:.4f} |\n"

    doc += f"""
## Reproducing

```bash
make setup models
make build LIMIT={args.samples and 260}    # generates the corpus (resumable)
make train
make ablate
make report
```

Seeds are fixed (`--seed 42`) and greedy decoding is used for the scored
generation, so a rebuild reproduces these rows. Note that Ollama's Metal
backend shows small floating-point non-determinism in logprobs across runs
(order 1e-3 nats); answers are stable, feature values move slightly.
"""

    Path(args.out).write_text(doc)
    print(f"wrote {args.out}")
    print(full.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

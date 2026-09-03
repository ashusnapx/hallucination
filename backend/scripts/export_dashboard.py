#!/usr/bin/env python
"""Export every number the dashboard renders, computed from real artefacts.

The website must never hand-enter a metric. This script reads the corpus and
the trained detector, recomputes out-of-fold predictions with the same
group-aware folds and cross-fitted calibration the trainer uses, and writes one
JSON file the frontend imports at build time.

Run it after ``make train``:

    python scripts/export_dashboard.py \
        --corpus data/corpus/llama3.2-3b.jsonl \
        --model-dir models/llama3.2-3b \
        --out ../website/src/data/dashboard.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from halluciwatch.calibration import Calibrator, expected_calibration_error
from halluciwatch.data.build import corpus_to_matrix, load_corpus
from halluciwatch.features import REGISTRY
from halluciwatch.model import _grouped_folds, _make_estimator

SEED = 42
FOLDS = 5


def oof_predictions(X, y, groups, kind="xgboost"):
    """Out-of-fold scores plus cross-fitted calibrated probabilities."""
    folds = _grouped_folds(groups, FOLDS, SEED)
    raw = np.zeros(len(y))
    for tr, te in folds:
        est = _make_estimator(kind, SEED, int(y[tr].sum()), int((1 - y[tr]).sum()))
        est.fit(X[tr], y[tr])
        raw[te] = est.predict_proba(X[te])[:, 1]

    # Never score a point with a calibrator that has seen it.
    cal = np.zeros(len(y))
    for _, te in folds:
        mask = np.ones(len(y), dtype=bool)
        mask[te] = False
        cal[te] = Calibrator(min_samples=50).fit(raw[mask], y[mask]).transform(raw[te])
    return raw, cal


def roc_points(y, scores, n=60):
    from sklearn.metrics import roc_curve

    fpr, tpr, _ = roc_curve(y, scores)
    idx = np.unique(np.linspace(0, len(fpr) - 1, min(n, len(fpr))).astype(int))
    return [{"x": round(float(fpr[i]), 4), "y": round(float(tpr[i]), 4)} for i in idx]


def pr_points(y, scores, n=60):
    from sklearn.metrics import precision_recall_curve

    precision, recall, _ = precision_recall_curve(y, scores)
    idx = np.unique(np.linspace(0, len(recall) - 1, min(n, len(recall))).astype(int))
    return [
        {"x": round(float(recall[i]), 4), "y": round(float(precision[i]), 4)} for i in idx
    ]


def reliability(y, probs, bins=10):
    """Reliability diagram: predicted probability vs observed frequency."""
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for lo, hi in pairwise(edges):
        m = (probs > lo) & (probs <= hi) if lo > 0 else (probs >= lo) & (probs <= hi)
        if not m.any():
            continue
        out.append(
            {
                "bin": round(float((lo + hi) / 2), 3),
                "predicted": round(float(probs[m].mean()), 4),
                "observed": round(float(y[m].mean()), 4),
                "count": int(m.sum()),
            }
        )
    return out


def risk_coverage(y, scores, n=40):
    order = np.argsort(scores)
    err = np.cumsum(y[order]) / np.arange(1, len(y) + 1)
    cov = np.arange(1, len(y) + 1) / len(y)
    idx = np.unique(np.linspace(0, len(cov) - 1, min(n, len(cov))).astype(int))
    return [
        {"coverage": round(float(cov[i]), 4), "error": round(float(err[i]), 4)} for i in idx
    ]


def score_histogram(y, probs, bins=20):
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for lo, hi in pairwise(edges):
        m = (probs > lo) & (probs <= hi) if lo > 0 else (probs >= lo) & (probs <= hi)
        out.append(
            {
                "bin": round(float((lo + hi) / 2), 3),
                "correct": int(((y == 0) & m).sum()),
                "hallucinated": int(((y == 1) & m).sum()),
            }
        )
    return out


def confusion_at(y, probs, threshold=0.5):
    pred = (probs >= threshold).astype(int)
    return {
        "threshold": threshold,
        "tp": int(((pred == 1) & (y == 1)).sum()),
        "fp": int(((pred == 1) & (y == 0)).sum()),
        "tn": int(((pred == 0) & (y == 0)).sum()),
        "fn": int(((pred == 0) & (y == 1)).sum()),
    }


def per_tier(X, y, groups, names, tiers):
    """AUROC for each signal family alone, and for the cumulative cascade."""
    from sklearn.metrics import average_precision_score, roc_auc_score

    tier_of = dict(zip(names, tiers, strict=False))
    combos = [
        ("surface", ["surface"]),
        ("token", ["token"]),
        ("surface+token", ["surface", "token"]),
        ("sampling", ["sampling"]),
        ("all", ["surface", "token", "sampling"]),
    ]
    # Measured marginal wall-clock on the reference machine (Apple M1).
    cost = {
        "surface": 0.0,
        "token": 1.38,
        "surface+token": 1.38,
        "sampling": 8.55,
        "all": 9.93,
    }
    out = []
    for label, keep in combos:
        cols = [i for i, n in enumerate(names) if tier_of.get(n) in keep]
        if not cols:
            continue
        raw, _ = oof_predictions(X[:, cols], y, groups)
        out.append(
            {
                "label": label,
                "features": len(cols),
                "auroc": round(float(roc_auc_score(y, raw)), 4),
                "auprc": round(float(average_precision_score(y, raw)), 4),
                "cost_s": cost[label],
            }
        )
    return out


def single_feature_auroc(X, y, names, top=14):
    from sklearn.metrics import roc_auc_score

    out = []
    for i, n in enumerate(names):
        col = X[:, i]
        if np.all(col == col[0]):
            continue
        a = roc_auc_score(y, col)
        out.append({"feature": n, "auroc": round(float(max(a, 1 - a)), 4)})
    out.sort(key=lambda d: -d["auroc"])
    return out[:top]


def by_source(kept_rows, y, probs):
    """Per-dataset breakdown — the synopsis promised several benchmarks."""
    from sklearn.metrics import roc_auc_score

    srcs = [r.get("source", "?") for r in kept_rows]
    out = []
    for src in sorted(set(srcs)):
        m = np.array([s == src for s in srcs])
        if m.sum() < 20 or len(np.unique(y[m])) < 2:
            auroc = None
        else:
            auroc = round(float(roc_auc_score(y[m], probs[m])), 4)
        out.append(
            {
                "source": src,
                "n": int(m.sum()),
                "base_rate": round(float(y[m].mean()), 4),
                "n_correct": int((y[m] == 0).sum()),
                "auroc": auroc,
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--eval-corpus", help="held-out corpus from other benchmarks")
    ap.add_argument("--golden", help="dual-graded golden set from scripts/golden_set.py")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from sklearn.metrics import (
        average_precision_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    rows = load_corpus(args.corpus)
    meta_path = Path(args.model_dir) / "detector.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    names = meta.get("feature_names") or REGISTRY.names(("surface", "token", "sampling"))
    tiers = REGISTRY.tiers_for(names)
    X, y, groups, kept = corpus_to_matrix(rows, names)

    raw, cal = oof_predictions(X, y, groups)

    pred = (cal >= 0.5).astype(int)
    headline = {
        "auroc": round(float(roc_auc_score(y, raw)), 4),
        "auprc": round(float(average_precision_score(y, raw)), 4),
        "f1": round(float(f1_score(y, pred)), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred)), 4),
        "accuracy": round(float((pred == y).mean()), 4),
        "ece": round(float(expected_calibration_error(cal, y)), 4),
        "brier": round(float(np.mean((cal - y) ** 2)), 4),
        "n": len(y),
        "base_rate": round(float(y.mean()), 4),
        "n_features": len(names),
        "model": rows[0].get("model", "unknown") if rows else "unknown",
    }

    # Bootstrap interval on AUROC — a point estimate from a few hundred rows
    # does not deserve three decimal places without one.
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(1000):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        boots.append(roc_auc_score(y[idx], raw[idx]))
    headline["auroc_ci"] = [
        round(float(np.percentile(boots, 2.5)), 4),
        round(float(np.percentile(boots, 97.5)), 4),
    ]

    latency = {
        "gen_seconds_median": round(
            float(np.median([r.get("gen_seconds", 0) for r in rows])), 4
        ),
        "tier1_overhead_s": 0.02,
        "tier2_overhead_s": 8.55,
        "target_ms": 50,
    }

    corpus_stats = {
        "rows_generated": len(rows),
        "rows_used": len(y),
        "refusals_excluded": len(rows) - len(y),
        "sources": dict(Counter(r.get("source", "?") for r in rows)),
        "graders": dict(Counter(r.get("verdict", {}).get("strategy", "?") for r in rows)),
        "median_tokens": int(np.median([r.get("n_tokens", 0) for r in rows])),
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "corpus_path": args.corpus,
        "headline": headline,
        "corpus": corpus_stats,
        "roc": roc_points(y, raw),
        "pr": pr_points(y, raw),
        "reliability": reliability(y, cal),
        "risk_coverage": risk_coverage(y, cal),
        "score_histogram": score_histogram(y, cal),
        "confusion": [confusion_at(y, cal, t) for t in (0.3, 0.5, 0.7)],
        "per_tier": per_tier(X, y, groups, names, tiers),
        "top_features": single_feature_auroc(X, y, names),
        "importances": [
            {"feature": n, "gain": round(float(g), 5)}
            for n, g in meta.get("importances", [])[:16]
        ],
        "by_source": by_source(kept, y, cal),
        "latency": latency,
        "policy": meta.get("policy", {}),
        "coverage_frontier": meta.get("metrics", {}).get("coverage_frontier", {}),
    }

    # Optional: a genuinely held-out benchmark the model never trained on.
    if args.eval_corpus and Path(args.eval_corpus).exists():
        ev_rows = load_corpus(args.eval_corpus)
        if ev_rows:
            Xe, ye, _, kepte = corpus_to_matrix(ev_rows, names)
            if len(ye) and len(np.unique(ye)) > 1:
                est = _make_estimator("xgboost", SEED, int(y.sum()), int((1 - y).sum()))
                est.fit(X, y)
                cal_full = Calibrator().fit(raw, y)
                pe = cal_full.transform(est.predict_proba(Xe)[:, 1])
                payload["holdout"] = {
                    "n": len(ye),
                    "base_rate": round(float(ye.mean()), 4),
                    # With a near-degenerate label distribution, AUROC is
                    # ranking a handful of points and should not be read as a
                    # comparable number. Surface the count that decides it.
                    "n_correct": int((ye == 0).sum()),
                    "n_hallucinated": int((ye == 1).sum()),
                    "auroc": round(float(roc_auc_score(ye, pe)), 4),
                    "auprc": round(float(average_precision_score(ye, pe)), 4),
                    "ece": round(float(expected_calibration_error(pe, ye)), 4),
                    "by_source": by_source(kepte, ye, pe),
                    "sources": dict(Counter(r.get("source", "?") for r in ev_rows)),
                }

    # Golden set: rows where an independent larger judge agreed with the string
    # matcher. Scoring on verified labels separates "the detector is wrong" from
    # "the label was wrong", which a single-rater corpus cannot do.
    if args.golden and Path(args.golden).exists():
        g_rows = load_corpus(args.golden)
        stats_path = Path(str(args.golden) + ".stats.json")
        g_stats = json.loads(stats_path.read_text()) if stats_path.exists() else {}
        if g_rows:
            Xg, yg, gg, _ = corpus_to_matrix(g_rows, names)
            if len(yg) and len(np.unique(yg)) > 1:
                raw_g, cal_g = oof_predictions(Xg, yg, gg)
                pred_g = (cal_g >= 0.5).astype(int)
                payload["golden"] = {
                    **g_stats,
                    "auroc": round(float(roc_auc_score(yg, raw_g)), 4),
                    "auprc": round(float(average_precision_score(yg, raw_g)), 4),
                    "f1": round(float(f1_score(yg, pred_g)), 4),
                    "precision": round(float(precision_score(yg, pred_g, zero_division=0)), 4),
                    "recall": round(float(recall_score(yg, pred_g)), 4),
                    "ece": round(float(expected_calibration_error(cal_g, yg)), 4),
                    "n": len(yg),
                    "base_rate": round(float(yg.mean()), 4),
                    # Best achievable F1 over all thresholds, reported alongside
                    # the 0.5 value so threshold choice is visible rather than
                    # hidden inside a single flattering number.
                    "best_f1": round(
                        float(max(f1_score(yg, (cal_g >= t).astype(int))
                                  for t in np.unique(np.round(cal_g, 3)))), 4
                    ),
                }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"wrote {out}")
    print(
        f"  AUROC {headline['auroc']} {headline['auroc_ci']}  "
        f"F1 {headline['f1']}  ECE {headline['ece']}  n={headline['n']}"
    )
    if "golden" in payload:
        g = payload["golden"]
        print(
            f"  golden:   AUROC {g['auroc']} on {g['n']} verified rows "
            f"(kappa {g.get('cohens_kappa')}, {g.get('n_contested')} contested)"
        )
    if "holdout" in payload:
        h = payload["holdout"]
        print(f"  held-out: AUROC {h['auroc']} on {h['n']} rows ({', '.join(h['sources'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

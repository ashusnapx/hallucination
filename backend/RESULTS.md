# Results

Generated 2026-09-03 05:45 UTC by `scripts/report.py`. Every number is computed from
`data/corpus/llama3.2-3b.jsonl` and `models/llama3.2-3b`; nothing here is hand-entered.

## Corpus

| property | value |
| --- | --- |
| rows generated | 520 |
| refusals excluded | 10 (1.9%) |
| rows used for training | 510 |
| hallucination base rate | 51.8% |
| models | llama3.2:3b (520) |
| sources | trivia_qa (260), nq_open (260) |
| grader decisions | fuzzy: 269, exact: 241, refusal: 10 |

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
| AUROC | 0.776 [0.734, 0.815] | ranking quality; 0.5 is chance |
| AUPRC | 0.771 | precision-recall area (base rate 51.8%) |
| F1 @ 0.5 | 0.747 | at the default probability threshold |
| Brier | 0.197 | squared error of the calibrated probability |
| ECE | 0.048 | calibration gap after cross-fitted isotonic; lower is better |
| AURC | 0.340 | area under risk-coverage; lower is better |

The 95% interval is a percentile bootstrap over 510 rows. With a corpus
this size the interval is wide enough that small differences between
configurations are not meaningful.

## Risk-coverage

If you auto-accept the answers the detector considers safest, this is the error
rate you inherit:

| auto-accept coverage | error rate among accepted |
| --- | --- |
| 20% | 26.5% |
| 40% | 25.0% |
| 50% | 32.5% |
| 60% | 37.9% |
| 80% | 43.9% |
| 100% | 51.8% |

## What each signal tier buys

```
tiers                        feats   AUROC          95% CI   AUPRC   cost/q  ΔAUROC/s
----------------------------------------------------------------------------------------
surface                          8   0.578 [0.526,0.630]   0.606    0.00s   baseline
token                           19   0.764 [0.718,0.806]   0.761    1.38s    0.1348
surface+token                   27   0.760 [0.714,0.803]   0.750    1.38s    0.1315
sampling                         9   0.739 [0.691,0.778]   0.743    8.55s    0.0188
surface+token+sampling          36   0.776 [0.733,0.813]   0.771    9.93s    0.0199
```

Cost is the measured marginal latency per query on an Apple M1
(`top_logprobs` penalty for the token tier, one generation per sample for the
sampling tier).

## Strongest individual features

| feature | AUROC alone | tier |
| --- | --- | --- |
| `tok.p90_entropy` | 0.789 | token |
| `tok.max_entropy` | 0.783 | token |
| `tok.min_top1` | 0.782 | token |
| `cns.mean_similarity` | 0.777 | sampling |
| `tok.mean_entropy` | 0.776 | token |
| `tok.mean_surprisal` | 0.774 | token |
| `tok.perplexity` | 0.774 | token |
| `tok.mean_top1` | 0.772 | token |
| `tok.max_content_entropy` | 0.769 | token |
| `cns.top_mass` | 0.765 | sampling |
| `cns.min_similarity` | 0.764 | sampling |
| `cns.semantic_entropy` | 0.764 | sampling |

A single feature scoring close to the full model is a useful warning: it means
the ensemble is adding little, and the cheap path is most of the value.

## Feature importances (trained model)

| feature | gain |
| --- | --- |
| `cns.mean_similarity` | 0.1278 |
| `cns.min_similarity` | 0.0886 |
| `tok.p90_entropy` | 0.0560 |
| `cns.top_mass` | 0.0427 |
| `tok.first_token_entropy` | 0.0349 |
| `srf.digit_density` | 0.0342 |
| `tok.max_content_entropy` | 0.0336 |
| `tok.mean_entropy` | 0.0334 |
| `tok.n_tokens` | 0.0330 |
| `tok.mean_content_entropy` | 0.0325 |
| `tok.min_top1` | 0.0323 |
| `srf.n_words` | 0.0323 |

## Reproducing

```bash
make setup models
make build LIMIT=260    # generates the corpus (resumable)
make train
make ablate
make report
```

Seeds are fixed (`--seed 42`) and greedy decoding is used for the scored
generation, so a rebuild reproduces these rows. Note that Ollama's Metal
backend shows small floating-point non-determinism in logprobs across runs
(order 1e-3 nats); answers are stable, feature values move slightly.

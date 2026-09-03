# Results

Generated 2026-09-03 08:15 UTC by `scripts/report.py`. Every number is computed from
`data/corpus/golden.jsonl` and `models/llama3.2-3b-golden`; nothing here is hand-entered.

## Corpus

| property | value |
| --- | --- |
| rows generated | 448 |
| refusals excluded | 0 (0.0%) |
| rows used for training | 448 |
| hallucination base rate | 50.9% |
| models | llama3.2:3b (448) |
| sources | trivia_qa (247), nq_open (201) |
| grader decisions | fuzzy: 230, exact: 218 |

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
| AUROC | 0.818 [0.778, 0.859] | ranking quality; 0.5 is chance |
| AUPRC | 0.823 | precision-recall area (base rate 50.9%) |
| F1 @ 0.5 | 0.758 | at the default probability threshold |
| Brier | 0.180 | squared error of the calibrated probability |
| ECE | 0.077 | calibration gap after cross-fitted isotonic; lower is better |
| AURC | 0.309 | area under risk-coverage; lower is better |

The 95% interval is a percentile bootstrap over 448 rows. With a corpus
this size the interval is wide enough that small differences between
configurations are not meaningful.

## Risk-coverage

If you auto-accept the answers the detector considers safest, this is the error
rate you inherit:

| auto-accept coverage | error rate among accepted |
| --- | --- |
| 20% | 20.2% |
| 40% | 26.8% |
| 50% | 25.9% |
| 60% | 30.6% |
| 80% | 42.5% |
| 100% | 50.9% |

## What each signal tier buys

```
tiers                        feats   AUROC          95% CI   AUPRC   cost/q  ΔAUROC/s
----------------------------------------------------------------------------------------
surface                          8   0.588 [0.538,0.641]   0.586    0.00s   baseline
token                           19   0.810 [0.772,0.850]   0.806    1.38s    0.1609
surface+token                   27   0.810 [0.771,0.850]   0.803    1.38s    0.1603
sampling                         9   0.775 [0.728,0.820]   0.805    8.55s    0.0219
surface+token+sampling          36   0.818 [0.779,0.857]   0.823    9.93s    0.0232
```

Cost is the measured marginal latency per query on an Apple M1
(`top_logprobs` penalty for the token tier, one generation per sample for the
sampling tier).

## Strongest individual features

| feature | AUROC alone | tier |
| --- | --- | --- |
| `tok.p90_entropy` | 0.823 | token |
| `tok.max_entropy` | 0.817 | token |
| `tok.min_top1` | 0.815 | token |
| `tok.mean_surprisal` | 0.811 | token |
| `tok.perplexity` | 0.811 | token |
| `cns.mean_similarity` | 0.809 | sampling |
| `tok.mean_entropy` | 0.809 | token |
| `tok.max_content_entropy` | 0.806 | token |
| `tok.mean_top1` | 0.803 | token |
| `cns.min_similarity` | 0.797 | sampling |
| `tok.mean_content_entropy` | 0.796 | token |
| `tok.first_token_entropy` | 0.795 | token |

A single feature scoring close to the full model is a useful warning: it means
the ensemble is adding little, and the cheap path is most of the value.

## Feature importances (trained model)

| feature | gain |
| --- | --- |
| `cns.exact_agreement` | 0.2186 |
| `cns.min_similarity` | 0.1677 |
| `tok.p90_entropy` | 0.1165 |
| `cns.mean_similarity` | 0.0717 |
| `tok.min_top1` | 0.0559 |
| `tok.mean_content_entropy` | 0.0471 |
| `tok.min_margin` | 0.0332 |
| `cns.semantic_entropy` | 0.0325 |
| `tok.max_content_entropy` | 0.0294 |
| `tok.first_token_entropy` | 0.0282 |
| `tok.mean_entropy` | 0.0214 |
| `tok.mean_surprisal` | 0.0186 |

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

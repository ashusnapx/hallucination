# HalluciWatch

**The missing runtime layer between the hallucination-detection literature and production guardrails.**

HalluciWatch reads the signals your local model already computes while it answers —
the shape of its token probability distribution, and how much its answer changes
when you ask again — and turns them into a **calibrated risk score** before the
answer reaches the user.

No API keys. No judge LLM. No vector database. No retrieval index.
The model runs on your machine through [Ollama](https://ollama.com) and scores itself.

```bash
pip install halluciwatch
ollama pull llama3.2:3b && ollama pull nomic-embed-text
halluciwatch score "Where was the Fiddler in the musical's title?"
```

Real output, `llama3.2:3b`, trained detector:

```
Q  Where was the Fiddler in the musical's title?
A  On a violin.

   risk    █████████████████████████░░░  0.881 (reject)
   tiers   surface+token   latency 1.12s (overhead 0.02s)
   note    tier-1 risk 0.88 outside escalation band [0.2, 0.8]; skipped sampling
```

It is *On the Roof*. The model is fluent, confident and wrong — and the whole
judgement cost **20 milliseconds on top of a generation that had to happen
anyway**, because the cheap token-distribution signals were already decisive and
the cascade never paid for the expensive tier.

When the cheap signals are *not* decisive, it escalates:

```
Q  Who was the 14th person to walk on the surface of the Moon?
A  I don't have information on the specific order in which people walked on the
   Moon's surface. A total of 12 astronauts walked on the Moon.

   risk    ████████░░░░░░░░░░░░░░░░░░░░  0.292 (abstain)
   tiers   surface+token+sampling   latency 16.74s (overhead 11.59s)
   note    the model declined to answer; a refusal makes no factual claim,
           so the risk score does not apply
```

A refusal gets its own verdict rather than a risk score — it asserts nothing
that could be unsupported.

---

## Why this exists

Every mainstream guardrail and eval tool — Guardrails AI, NeMo Guardrails,
DeepEval, RAGAS, TruLens, Opik, Langfuse — is strictly **black-box**. It re-reads
the model's text output, usually with a second LLM call that costs money and
latency. Meanwhile a large research literature
([SAPLMA](https://arxiv.org/abs/2304.13734),
[INSIDE/EigenScore](https://arxiv.org/abs/2402.03744),
[MIND](https://arxiv.org/abs/2403.06448),
[semantic entropy](https://www.nature.com/articles/s41586-024-07421-0),
[LLM-Check](https://openreview.net/forum?id=LYx4w3CAgy),
[RAUQ](https://arxiv.org/abs/2505.20045)) shows the generator's own internals
predict hallucination well — and has almost **zero production surface area**.

> **On novelty, honestly.** This project's original synopsis claimed that "no
> existing system uses a model's own internal neural signals to predict
> hallucination risk in real-time." That claim is false, and it is worth stating
> plainly. [MIND (2024)](https://arxiv.org/abs/2403.06448) is titled
> *"Unsupervised Real-Time Hallucination Detection based on the Internal States
> of Large Language Models."*
> [LM-Polygraph](https://github.com/IINemo/lm-polygraph) ships ~49 uncertainty
> estimators including attention- and hidden-state-based ones.
>
> The defensible gap is not scientific priority — it is engineering. Nobody has
> packaged these signals into a **cost-aware, calibrated runtime guardrail with
> statistical abstention guarantees that runs on a laptop**. That is what this is.

## What is actually new here

**1. A cost-aware cascade.** The literature reports detection quality without a
cost axis. Signal families here differ in cost by ~100×, and the expensive ones
are not uniformly better — they are better on *different questions*. So the
detector escalates instead of always paying:

| tier | signals | measured cost |
| --- | --- | --- |
| 0 · surface | refusal detection, hedging, length, entity density | free |
| 1 · token | entropy, varentropy, margin, perplexity, content-token entropy | **+5%** wall-time (see below) |
| 2 · sampling | semantic entropy, self-consistency, cluster agreement | **+K generations** |
| 3 · verify | P(True) self-evaluation | +1 generation *(off by default — see below)* |

Tiers 0–1 run on every request. Tier 2 runs only when the cheap score lands in an
uncertainty band, so the average query costs far less than the worst case.

**2. Calibration and conformal abstention.** A raw classifier score is not a
probability, and 0.5 is an arbitrary threshold. Scores go through isotonic
calibration, and the accept/reject thresholds are fitted on held-out data so that
the error rate *among auto-accepted answers* is bounded at a target you choose.
That converts "risk = 0.73" into "auto-accept this 60% of traffic and inherit
≤10% factual error."

**3. An honest cost/quality frontier.** `halluciwatch ablate` measures what each
tier actually buys on *your* model and data, in AUROC per second. The design
above is a consequence of that measurement, not an assumption.

---

## Three findings that shaped the design

These came out of building it, and each one changes what the code does.

### `top_logprobs` is free-or-full — never ask for k between 1 and 19

Measured on an M1, `llama3.2:1b`, 60 generated tokens, median of 5 runs:

| request | median wall-time | overhead |
| --- | --- | --- |
| no logprobs | 1.710 s | — |
| `logprobs`, `top_logprobs=0` | 1.799 s | **+5.2%** |
| `top_logprobs=1` | 3.030 s | +77.2% |
| `top_logprobs=5` | 3.103 s | +81.4% |
| `top_logprobs=20` | 3.091 s | +80.7% |

The penalty for requesting *any* alternatives is essentially fixed — it does not
scale with k. So the cheap path uses `top_logprobs=0` (chosen-token surprisal
only, +5%), and the rich path takes the maximum 20, because k=1 costs the same
as k=20. Encoded in [`backends/ollama.py`](src/halluciwatch/backends/ollama.py).

### Ollama does not lower-case for uncased embedding models — and it silently destroys semantic clustering

`nomic-embed-text` is a BERT-family **uncased** model, but Ollama 0.13.4 does not
lower-case input before tokenising, so every capitalised token becomes `[UNK]`.
Unrelated strings collapse onto the same vector:

| pair | raw cosine | lower-cased |
| --- | --- | --- |
| "The capital of France is Paris." vs "The capital of Japan is Tokyo." | **1.0000** | 0.7212 |
| "John Logie Baird" vs "Philo Farnsworth" | **0.9786** | 0.4020 |
| "The capital of France is Paris." vs "Paris is the French capital city." | 0.9570 | 0.9697 |

Two different facts scored as *identical*, while a true paraphrase scored lower
than two unrelated people. Every semantic-consistency feature built on this would
have been noise that looked like a working signal — exactly the failure mode this
project exists to catch. `OllamaBackend.embed()` lower-cases unconditionally.

### P(True) self-verification is worthless at 1B scale — and adding it *hurts*

On 40 TriviaQA questions with `llama3.2:1b`, asking the model to grade its own
answer scored **AUROC 0.500** — exactly chance (mean 0.527 on correct answers,
0.530 on wrong ones). Adding it to the tier-1 feature set *reduced* cross-validated
AUROC from 0.872 to 0.841, because an uninformative feature is not free.

This matches [Kadavath et al.](https://arxiv.org/abs/2207.05221), where
self-evaluation ability emerges with scale. Tier 3 is therefore **off by default**,
and `halluciwatch ablate` exists so the decision is made from your data rather
than from the literature's defaults.

---

## Install

```bash
# 1. Ollama with a local model
brew install ollama && ollama serve
ollama pull llama3.2:3b        # generator (~2GB, comfortable on 8GB RAM)
ollama pull nomic-embed-text   # embeddings for semantic clustering (~274MB)

# 2. The package
pip install "halluciwatch[all]"
halluciwatch doctor            # verifies connectivity, models, logprobs, embeddings
```

The core install needs only `httpx` and `numpy` — nothing pulls in torch or
transformers, because the model runs in Ollama rather than in this process.

## Use

### Library

```python
from halluciwatch import HallucinationDetector

with HallucinationDetector() as detector:
    report = detector.score("Who discovered penicillin?")

    print(report.risk)        # 0.0-1.0, calibrated when a model is loaded
    print(report.decision)    # accept | review | reject
    print(report.answer)
    print(report.top_factors) # which signals drove the score
    print(report.clusters)    # the distinct answers, when the cascade escalated
```

Untrained, the detector still works — it falls back to a transparent heuristic
over token and semantic entropy and marks the report `calibrated=False`. Train on
your own model for a real probability.

### End-to-end

```bash
make setup models      # venv + pull models
make build             # generate a labelled corpus (resumable)
make train             # fit + calibrate, prints CV metrics
make ablate            # what did each tier buy?
make refresh           # recompute features from stored samples, no regeneration
make dashboard         # export every metric to the website as JSON
make report            # regenerate RESULTS.md from the artefacts
make serve             # HTTP API on :8000
```

### HTTP API

```bash
halluciwatch serve --model-dir models/llama3.2-3b
curl -s localhost:8000/score -H 'content-type: application/json' \
     -d '{"question":"Who invented the telephone?"}' | jq
```

`GET /features` documents every feature and its tier. `POST /score/stream` emits
server-sent events so a UI can show the answer immediately and the risk when
scoring completes.

---

## How labels are made

This is where a detector project most often goes quietly wrong, so it is explicit.

Questions come from datasets with **gold short answers**
(TriviaQA, NQ-Open, TruthfulQA, SimpleQA). The local model answers each one; the
answer is graded against the gold aliases by normalised exact match, then token-F1,
then optionally an LLM judge. `label = 1` means the model's answer was not
supported.

Two deliberate choices:

* **Refusals are excluded, not labelled.** "I don't know" is neither a
  hallucination nor a correct answer, and labelling it either way teaches the
  detector something false. It is also the case that consistent refusal is
  *indistinguishable from consistent knowledge* to every consistency-based
  signal — which is why `srf.is_refusal` is a tier-0 feature.
* **Cross-validation is grouped by question.** Letting one question appear in
  both train and test leaks its difficulty and inflates AUROC by several points.

HaluEval is supported as a question source but with a caveat: its answers were
written by *other* models, and Ollama cannot return logprobs for text it did not
generate (`num_predict: 0` does not suppress generation), so the token tier is
unavailable on that path.

## Results

See [RESULTS.md](RESULTS.md), generated by `scripts/report.py` from the corpus
and the trained model, so the numbers in the repo cannot drift from the numbers
the code produces. `scripts/export_dashboard.py` writes the same measurements —
plus ROC, precision–recall, calibration and risk–coverage curves, the confusion
matrix and the per-source breakdown — to the website as JSON, so the dashboard
at `/dashboard` renders real data rather than transcribed numbers.

**Headline** — `llama3.2:3b`, 520 questions from TriviaQA and NQ-Open, 5-fold CV
grouped by question, 51.8% hallucination base rate:

| metric | value |
| --- | --- |
| AUROC | **0.776** [0.734, 0.815] |
| AUPRC | 0.771 |
| F1 @ 0.5 | 0.747 |
| ECE | 0.048 |
| Brier | 0.197 |

### The cascade, measured

This is the table the whole design rests on:

| tiers | features | AUROC | cost/query | ΔAUROC per second |
| --- | --- | --- | --- | --- |
| surface | 8 | 0.578 [0.526, 0.630] | 0.00s | baseline |
| **token** | 19 | **0.764** [0.718, 0.806] | **1.38s** | **0.135** |
| surface+token | 27 | 0.760 [0.714, 0.803] | 1.38s | 0.132 |
| sampling | 9 | 0.739 [0.691, 0.778] | 8.55s | 0.019 |
| surface+token+sampling | 36 | 0.776 [0.733, 0.813] | 9.93s | 0.020 |

**Adding semantic entropy costs 7× the latency for +0.012 AUROC, and the
confidence intervals overlap almost entirely.** On short-form QA with a 3B local
model, the cheap token signals are essentially the whole detector. That is not
the answer the literature would lead you to expect, and it is why the cascade
defaults to escalating only inside the uncertainty band rather than always
sampling.

Three further results worth stating plainly, because they are unflattering:

* **A single feature beats the ensemble.** `tok.p90_entropy` alone scores
  **0.789** — higher than all 36 features together (0.776). On 520 rows the
  gradient boosting is fitting noise. The honest reading is that most of the
  value here is one well-chosen uncertainty statistic, not a learned combination.
* **Surface features actively hurt.** `token` alone (0.764) beats
  `surface+token` (0.760).
* **The ≤10% error target is unreachable.** Even the safest-scored 5% of answers
  are ~18% wrong. The conformal policy correctly refuses to promise coverage it
  cannot deliver rather than quietly missing the target. At ≤30% error it
  auto-accepts 46.5% of traffic against a 51.8% base rate.

> **On the synopsis targets.** The original proposal targeted F1 > 0.85 and
> AUROC > 0.90. Measured here: **F1 0.747, AUROC 0.776** — short of both. Those
> literature numbers come from larger models with true white-box access (hidden
> states and attention), longer-form generations where semantic entropy has more
> to work with, and often easier label distributions. A 3B quantised model
> answering short-form trivia through a gray-box API is a harder setting, and
> reporting 0.776 with its confidence interval is more useful than tuning until
> a target is hit. Everything needed to re-run and disagree is in `make build
> && make train && make ablate`.

## Architecture

```
question
   │
   ▼
OllamaBackend.generate(logprobs=True, top_logprobs=20)     ← the answer you wanted
   │
   ├─ tier 0  surface features        (free)
   ├─ tier 1  token distribution      (+5% or +80%)
   │
   ├─ cheap risk in uncertainty band? ──no──► score
   │            │yes
   │            ▼
   ├─ tier 2  K samples → cluster by meaning → semantic entropy
   │
   ▼
fingerprint (38 named features) → gradient boosting → isotonic calibration
   │
   ▼
DecisionPolicy → accept / review / reject
```

| module | responsibility |
| --- | --- |
| [`backends/ollama.py`](src/halluciwatch/backends/ollama.py) | Ollama client; the two workarounds above live here |
| [`features/`](src/halluciwatch/features) | the four signal tiers, each self-documenting |
| [`cluster.py`](src/halluciwatch/cluster.py) | meaning-clustering for semantic entropy |
| [`detector.py`](src/halluciwatch/detector.py) | cascade orchestration |
| [`calibration.py`](src/halluciwatch/calibration.py) | isotonic calibration + conformal thresholds |
| [`model.py`](src/halluciwatch/model.py) | training, grouped CV, persistence |
| [`evaluation/`](src/halluciwatch/evaluation) | metrics, bootstrap CIs, tier ablation |

Every feature is declared in a registry with its tier and a description of what it
measures, so the fingerprint is ordered and stable — a model cannot be silently
scored against reordered features.

## Limitations

* **Short-form QA is the tested regime.** Long-form generation needs claim-level
  decomposition, which is not implemented.
* **Detection, not correction.** A high score tells you to distrust an answer, not
  what the right one is.
* **Confidently-wrong memorised falsehoods are the known blind spot** of every
  uncertainty-based method, this one included. If a model is uniformly certain of
  something false, no consistency or entropy signal will flag it.
* **Refusal detection is a regex.** Cheap by requirement; it will miss creative
  phrasings.
* **Ollama's Metal backend is not bit-deterministic.** Answers are stable under a
  fixed seed, but logprobs move by ~1e-3 nats between runs.

## Development

```bash
make setup && make test && make lint
```

Tests use hand-constructed distributions with known analytic answers rather than
random arrays, so a regression in the entropy or clustering maths fails loudly
instead of merely changing a shape.

## License

Apache-2.0.

## Acknowledgements

Builds directly on ideas from semantic entropy
([Kuhn et al. 2023](https://arxiv.org/abs/2302.09664);
[Farquhar et al., *Nature* 2024](https://www.nature.com/articles/s41586-024-07421-0)),
[SelfCheckGPT](https://arxiv.org/abs/2303.08896),
[P(True)](https://arxiv.org/abs/2207.05221), and the estimator bank assembled by
[LM-Polygraph](https://github.com/IINemo/lm-polygraph).

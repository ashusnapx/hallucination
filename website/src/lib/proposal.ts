/**
 * What the Phase-1 proposal promised, and what was actually delivered.
 *
 * Everything here is transcribed from the submitted synopsis and slide deck so
 * the dashboard can score the project against its own stated targets rather
 * than against a bar drawn after the fact. Where a target was missed, it says
 * missed.
 */

export type Status = "met" | "partial" | "missed" | "changed";

export interface Deliverable {
  id: string;
  promised: string;
  target: string;
  actual: string;
  status: Status;
  note: string;
}

export const STATUS_META: Record<
  Status,
  { label: string; token: "safe" | "caution" | "danger" | "neutral" }
> = {
  met: { label: "Met", token: "safe" },
  partial: { label: "Partial", token: "caution" },
  missed: { label: "Missed", token: "danger" },
  changed: { label: "Changed", token: "neutral" },
};

export const DELIVERABLES: Deliverable[] = [
  {
    id: "auroc",
    promised: "Trained classifier — ranking quality",
    target: "AUC-ROC > 0.90",
    actual: "0.776 [0.734, 0.815]",
    status: "missed",
    note: "Short of target. The literature's >0.90 comes from larger models with true white-box access and longer generations. A 3B quantised model answering short-form trivia through a gray-box API is a harder setting; the interval is reported rather than the point estimate alone.",
  },
  {
    id: "f1",
    promised: "Trained classifier — F1",
    target: "F1 > 0.85",
    actual: "0.747 at threshold 0.5",
    status: "missed",
    note: "Short of target. Precision 0.693, recall 0.811 — the detector is tuned to catch hallucinations rather than to avoid false alarms, which is the right trade for a guardrail.",
  },
  {
    id: "latency",
    promised: "Real-time wrapper overhead",
    target: "< 50 ms added latency",
    actual: "~20 ms (tier 1)",
    status: "partial",
    note: "The cheap path clears the target with room to spare: 0.02 s of scoring on top of a generation that had to happen anyway. The sampling tier costs K extra generations and cannot meet 50 ms by construction — which is exactly why it only runs inside the uncertainty band.",
  },
  {
    id: "signals",
    promised: "Internal neural signals",
    target:
      "Entropy, token probabilities, attention weights, hidden-layer activations",
    actual: "Entropy + token probabilities (19 features)",
    status: "partial",
    note: "Ollama exposes per-token logprobs with top-20 alternatives, but not attention maps or hidden states. Those two signal families are unreachable through this runtime; the architecture compensates with a self-consistency tier the proposal did not include.",
  },
  {
    id: "classifier",
    promised: "Lightweight classifier on fingerprint vectors",
    target: "XGBoost + scikit-learn",
    actual: "XGBoost, 36 features, isotonic-calibrated",
    status: "met",
    note: "Delivered, plus calibration and conformal accept/reject thresholds the proposal did not ask for. ECE 0.048 measured on cross-fitted held-out predictions.",
  },
  {
    id: "datasets",
    promised: "Benchmark validation",
    target: "HaluEval, TruthfulQA, SimpleQA, FEVER",
    actual: "2 for training, 2 scored held-out, 1 unusable",
    status: "partial",
    note: "Five loaders ship. TriviaQA and NQ-Open train the detector; TruthfulQA and SimpleQA were generated and scored entirely held out — but llama3.2:3b answers only 4 of 227 of them correctly, so they measure the generator rather than the detector. HaluEval's answers were written by other models and Ollama cannot return logprobs for text it did not generate, so the token tier is unavailable there. FEVER is claim verification rather than generation and does not fit a generation-time detector.",
  },
  {
    id: "pipeline",
    promised: "Four-phase pipeline",
    target: "Collect → extract → engineer → train",
    actual: "All four, reproducible with four make targets",
    status: "met",
    note: "make build → make train → make ablate → make report. Seeds fixed, corpus resumable, RESULTS.md generated from the artefacts so the repo's numbers cannot drift from the code's.",
  },
  {
    id: "library",
    promised: "Open-source library",
    target: "pip install halluciwatch",
    actual: "Apache-2.0, Python 3.10–3.13",
    status: "met",
    note: "Core install needs only httpx and numpy. Library, CLI and HTTP API, with 100 tests (86 unit, 14 integration against a live Ollama).",
  },
  {
    id: "demo",
    promised: "Interactive demo",
    target: "Streamlit / Gradio, live risk gauge + per-token entropy",
    actual: "Next.js app on a FastAPI backend",
    status: "changed",
    note: "Same surface — live risk gauge, per-token entropy heat-map, real-time scoring of any typed query — built as a real web app instead of a notebook UI. Streamlit was the proposal's guess at the interface, not a requirement of it.",
  },
  {
    id: "tracking",
    promised: "Experiment tracking",
    target: "MLflow",
    actual: "Versioned JSON artefacts + generated report",
    status: "changed",
    note: "Every run writes detector.json with metrics, per-tier ablation, feature importances and the exact config. MLflow's server and database were overhead this project could not justify on an 8 GB laptop.",
  },
  {
    id: "models",
    promised: "Evaluated models",
    target: "Llama 3.1 8B & Mistral 7B",
    actual: "llama3.2:3b (+ llama3.2:1b for the scale ablation)",
    status: "changed",
    note: "The reference machine has 8 GB of unified memory. An 8B model at 4-bit leaves no headroom for the K-sample tier, so the study ran on 3B and used 1B for the scale comparison that produced the P(True) finding.",
  },
];

/** The 15 papers from the Phase-1 literature review, as submitted. */
export const PAPERS = [
  {
    n: 1,
    topic: "Behavioral Fingerprinting",
    method: "Cognitive & interaction probing",
    finding:
      "Alignment behaviours (sycophancy) vary significantly; usable as fingerprints",
    group: "Fingerprinting",
  },
  {
    n: 2,
    topic: "Semantic Mapping",
    method: "Text embedding classification",
    finding:
      "Up to 89% accuracy identifying source LLM via semantic vector space",
    group: "Fingerprinting",
  },
  {
    n: 3,
    topic: "Active Querying (LLMmap)",
    method: "Crafted multi-turn query sequences",
    finding:
      "42 LLM versions identified with >95% accuracy from 8 interactions",
    group: "Fingerprinting",
  },
  {
    n: 4,
    topic: "Evaluative Fingerprints",
    method: "Disagreement pattern analysis",
    finding:
      "LLM-as-judge has stable evaluative dispositions acting as fingerprints",
    group: "Fingerprinting",
  },
  {
    n: 5,
    topic: "Prompt-Induced Fingerprints",
    method: "Statistical probability shift analysis",
    finding: "Malicious prompts create distinct linguistic shifts",
    group: "Fingerprinting",
  },
  {
    n: 6,
    topic: "Ensemble Attacks (TFA/SVA)",
    method: "Token filter & sentence verification attack",
    finding:
      "Fingerprint responses can be suppressed with minimal performance loss",
    group: "Fingerprinting",
  },
  {
    n: 7,
    topic: "Mimicry Limits",
    method: "Prompted stylistic imitation",
    finding:
      "LLMs fail full human profile replication; model fingerprints dominate",
    group: "Fingerprinting",
  },
  {
    n: 8,
    topic: "Hallucination Inevitability",
    method: "Mathematical structural analysis",
    finding: "Hallucinations are an inevitable feature of probabilistic design",
    group: "Detection",
  },
  {
    n: 9,
    topic: "Structural Hallucinations",
    method: "Pipeline-level analysis",
    finding:
      "Hallucinations arise at every stage, from data curation to retrieval",
    group: "Detection",
  },
  {
    n: 10,
    topic: "HalluMTBench",
    method: "Multilingual MT benchmark",
    finding: "Triggers linked to model scale and low-resource language bias",
    group: "Benchmarks",
  },
  {
    n: 11,
    topic: "HalluField (field-theoretic)",
    method: "Thermodynamics-inspired modelling",
    finding:
      "Semantic energy/entropy detects hallucination without ground-truth labels",
    group: "Detection",
  },
  {
    n: 12,
    topic: "LLM-Check (internal states)",
    method: "Hidden states & attention analysis",
    finding: "Hallucinations correlate with anomalies in internal activations",
    group: "Detection",
  },
  {
    n: 13,
    topic: "FPBENCH (multimodal)",
    method: "20-model multimodal benchmark",
    finding: "Major capability gaps in forensic fingerprint tasks",
    group: "Benchmarks",
  },
  {
    n: 14,
    topic: "LEAF BENCH (IP/copyright)",
    method: "Parameter-altered & distilled models",
    finding: "Model lineage traceable even after distillation",
    group: "Benchmarks",
  },
  {
    n: 15,
    topic: "Model Provenance Protection",
    method: "Cross-methodological review",
    finding:
      "No universal fingerprinting technique resists all adversarial attacks",
    group: "Detection",
  },
] as const;

/** The four phases from the methodology slide, with what each became. */
export const PHASES = [
  {
    n: "Phase 1",
    title: "Data collection",
    proposed:
      "Prompt Llama 3.1 8B & Mistral 7B with HaluEval and TruthfulQA. Label each response as hallucinated or correct.",
    built:
      "llama3.2:3b over TriviaQA and NQ-Open, graded by normalised exact match then token-F1 against gold aliases. Refusals excluded rather than labelled.",
  },
  {
    n: "Phase 2",
    title: "Signal extraction",
    proposed:
      "PyTorch hooks capturing entropy, token probability distributions, attention weights and hidden-layer activations.",
    built:
      "Ollama logprobs with top-20 alternatives per token. Attention and hidden states are not exposed by this runtime; a K-sample self-consistency tier covers what they would have.",
  },
  {
    n: "Phase 3",
    title: "Feature engineering",
    proposed:
      "Aggregate per-layer statistics into a fixed-length fingerprint vector.",
    built:
      "36 named features across three tiers, declared in a registry so the vector order is stable and a model cannot be scored against reordered features.",
  },
  {
    n: "Phase 4",
    title: "Classifier training",
    proposed:
      "Train XGBoost. Evaluate with F1, AUC-ROC, precision and recall. Deploy as a real-time wrapper.",
    built:
      "XGBoost with cross-validation grouped by question, isotonic calibration cross-fitted so ECE is honest, and conformal accept/reject thresholds. Served as a library, CLI and HTTP API.",
  },
] as const;

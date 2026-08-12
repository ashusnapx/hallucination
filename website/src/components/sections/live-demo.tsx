"use client";

import { useCallback, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Play,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  XCircle,
  HelpCircle,
  ChevronDown,
  Calculator,
  GitBranch,
  Sparkles,
  Clock,
  Cpu,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MermaidDiagram } from "@/components/mermaid-diagram";

/* ── Types mirroring the FastAPI response ─────────────────────────────── */

interface PipelineStepData {
  step_number: number;
  name: string;
  description: string;
  input_text: string;
  output_text: string;
  duration_ms: number;
  status: "ok" | "error";
  model_used: string;
  explanation: string;
}

interface ClaimDetail {
  index: number;
  claim: string;
  verdict: "CORRECT" | "INCORRECT" | "UNVERIFIABLE";
  reason: string;
  weight: number;
  contribution: number;
}

interface CalculationData {
  total_claims: number;
  correct: number;
  incorrect: number;
  unverifiable: number;
  weights: Record<string, number>;
  numerator: number;
  denominator: number;
  raw_score: number;
  risk_score: number;
  confidence: number;
  formula: string;
  substituted: string;
  steps_human: string[];
}

interface ScoreResult {
  risk_score: number;
  risk_label: string;
  confidence: number;
  total_latency_ms: number;
  response: string;
  question: string;
  factual_claims: string[];
  claim_verdicts: string[];
  claim_details: ClaimDetail[];
  verification_notes: string;
  model_used: string;
  calculation: CalculationData | null;
  mermaid: string;
  steps: PipelineStepData[];
  degraded: boolean;
  error?: string | null;
}

const demoQuestions = [
  "Cite the legal case 'Royer v. Nelson, 2007 UT App 74' and summarize its ruling.",
  "What was the outcome of the 2024 UN Global AI Safety Summit in Geneva?",
  "List three peer-reviewed studies published in Nature in 2025 about quantum error correction.",
  "What are the exact casualty figures from the 2025 Bangladesh cyclone?",
  "Summarize the key findings of the 2026 WHO report on microplastics in drinking water.",
  "What is the capital of France and what is it known for?",
];

/* ── Small presentational helpers ─────────────────────────────────────── */

const verdictStyles = {
  CORRECT: {
    icon: CheckCircle2,
    ring: "border-emerald-500/25 bg-emerald-500/[0.07]",
    text: "text-emerald-300",
    chip: "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
    dot: "bg-emerald-400",
  },
  INCORRECT: {
    icon: XCircle,
    ring: "border-red-500/25 bg-red-500/[0.07]",
    text: "text-red-300",
    chip: "bg-red-500/15 text-red-300 border-red-500/25",
    dot: "bg-red-400",
  },
  UNVERIFIABLE: {
    icon: HelpCircle,
    ring: "border-amber-500/25 bg-amber-500/[0.07]",
    text: "text-amber-300",
    chip: "bg-amber-500/15 text-amber-300 border-amber-500/25",
    dot: "bg-amber-400",
  },
} as const;

function riskTone(pct: number) {
  if (pct < 30)
    return {
      text: "risk-low",
      bar: "from-emerald-500 to-green-400",
      label: "Low risk — the answer holds up",
      Icon: CheckCircle2,
      chip: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300",
    };
  if (pct < 70)
    return {
      text: "risk-medium",
      bar: "from-amber-500 to-yellow-400",
      label: "Medium risk — verify before trusting",
      Icon: AlertTriangle,
      chip: "border-amber-500/25 bg-amber-500/10 text-amber-300",
    };
  return {
    text: "risk-high",
    bar: "from-orange-500 to-red-500",
    label: "High risk — likely hallucination",
    Icon: AlertTriangle,
    chip: "border-red-500/25 bg-red-500/10 text-red-300",
  };
}

function SectionHeading({
  icon: Icon,
  title,
  hint,
}: {
  icon: React.ElementType;
  title: string;
  hint?: string;
}) {
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-primary" />
        <h4 className="font-[family-name:var(--font-geist-mono)] text-xs font-semibold tracking-widest text-foreground uppercase">
          {title}
        </h4>
      </div>
      {hint && <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{hint}</p>}
    </div>
  );
}

function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

/* ── Pipeline step (expandable) ───────────────────────────────────────── */

function StepCard({ step, index }: { step: PipelineStepData; index: number }) {
  const [open, setOpen] = useState(false);
  const failed = step.status === "error";

  return (
    <Reveal delay={0.05 * index}>
      <div
        className={`rounded-xl border transition-colors ${
          failed ? "border-red-500/30 bg-red-500/[0.04]" : "border-border/60 bg-card/40"
        }`}
      >
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-start gap-3 p-4 text-left"
          aria-expanded={open}
        >
          <span
            className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg font-[family-name:var(--font-geist-mono)] text-xs font-bold ${
              failed ? "bg-red-500/15 text-red-300" : "bg-primary/15 text-primary"
            }`}
          >
            {step.step_number}
          </span>

          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold">{step.name}</span>
              {step.model_used && step.model_used !== "—" && (
                <span className="inline-flex items-center gap-1 rounded-md bg-muted/60 px-1.5 py-0.5 font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground">
                  <Cpu className="h-2.5 w-2.5" />
                  {step.model_used}
                </span>
              )}
              {step.duration_ms > 0 && (
                <span className="inline-flex items-center gap-1 font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground">
                  <Clock className="h-2.5 w-2.5" />
                  {step.duration_ms.toFixed(0)}ms
                </span>
              )}
            </span>
            <span className="mt-1 block text-xs text-muted-foreground">{step.description}</span>
          </span>

          <ChevronDown
            className={`mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform ${
              open ? "rotate-180" : ""
            }`}
          />
        </button>

        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="space-y-3 border-t border-border/50 px-4 pt-4 pb-4">
                {step.explanation && (
                  <div className="rounded-lg border border-primary/15 bg-primary/[0.05] p-3">
                    <p className="text-xs leading-relaxed text-foreground/85">
                      <span className="font-semibold text-primary">Why this step matters — </span>
                      {step.explanation}
                    </p>
                  </div>
                )}
                <div>
                  <p className="mb-1.5 font-[family-name:var(--font-geist-mono)] text-[10px] tracking-widest text-muted-foreground uppercase">
                    Input
                  </p>
                  <pre className="max-h-40 overflow-auto rounded-lg bg-black/30 p-3 font-[family-name:var(--font-geist-mono)] text-[11px] leading-relaxed whitespace-pre-wrap text-muted-foreground">
                    {step.input_text || "—"}
                  </pre>
                </div>
                <div>
                  <p className="mb-1.5 font-[family-name:var(--font-geist-mono)] text-[10px] tracking-widest text-muted-foreground uppercase">
                    Output
                  </p>
                  <pre
                    className={`max-h-56 overflow-auto rounded-lg bg-black/30 p-3 font-[family-name:var(--font-geist-mono)] text-[11px] leading-relaxed whitespace-pre-wrap ${
                      failed ? "text-red-300" : "text-foreground/80"
                    }`}
                  >
                    {step.output_text || "—"}
                  </pre>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Reveal>
  );
}

/* ── The math, spelled out ────────────────────────────────────────────── */

function MathBreakdown({ calc, details }: { calc: CalculationData; details: ClaimDetail[] }) {
  const pct = Math.round(calc.risk_score * 100);

  return (
    <div className="space-y-5">
      {/* Tally */}
      <div className="grid grid-cols-3 gap-3">
        {(
          [
            ["CORRECT", calc.correct, "0.0"],
            ["UNVERIFIABLE", calc.unverifiable, "0.3"],
            ["INCORRECT", calc.incorrect, "0.8"],
          ] as const
        ).map(([verdict, count, weight]) => {
          const s = verdictStyles[verdict];
          return (
            <div key={verdict} className={`rounded-xl border p-3 text-center ${s.ring}`}>
              <div className={`font-[family-name:var(--font-display)] text-2xl font-bold ${s.text}`}>
                {count}
              </div>
              <div className="mt-0.5 font-[family-name:var(--font-geist-mono)] text-[9px] tracking-wider text-muted-foreground uppercase">
                {verdict}
              </div>
              <div className="mt-1.5 font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground">
                weight {weight}
              </div>
            </div>
          );
        })}
      </div>

      {/* Per-claim contributions */}
      <div className="overflow-hidden rounded-xl border border-border/60">
        <div className="grid grid-cols-[2rem_1fr_5.5rem_3.5rem] gap-2 border-b border-border/60 bg-muted/40 px-3 py-2 font-[family-name:var(--font-geist-mono)] text-[10px] tracking-wider text-muted-foreground uppercase">
          <span>#</span>
          <span>Claim</span>
          <span className="text-center">Verdict</span>
          <span className="text-right">Weight</span>
        </div>
        {details.map((d) => {
          const s = verdictStyles[d.verdict] ?? verdictStyles.UNVERIFIABLE;
          return (
            <div
              key={d.index}
              className="grid grid-cols-[2rem_1fr_5.5rem_3.5rem] items-center gap-2 border-b border-border/40 px-3 py-2.5 last:border-0"
            >
              <span className="font-[family-name:var(--font-geist-mono)] text-[11px] text-muted-foreground">
                {d.index}
              </span>
              <span className="text-xs leading-snug">{d.claim}</span>
              <span
                className={`justify-self-center rounded-md border px-1.5 py-0.5 font-[family-name:var(--font-geist-mono)] text-[9px] font-semibold ${s.chip}`}
              >
                {d.verdict.slice(0, 5)}
              </span>
              <span
                className={`text-right font-[family-name:var(--font-geist-mono)] text-xs font-semibold ${
                  d.weight > 0 ? s.text : "text-muted-foreground"
                }`}
              >
                +{d.weight.toFixed(1)}
              </span>
            </div>
          );
        })}
      </div>

      {/* The formula */}
      <div className="rounded-xl border border-primary/25 bg-primary/[0.05] p-4">
        <p className="mb-3 font-[family-name:var(--font-geist-mono)] text-[10px] tracking-widest text-primary uppercase">
          The formula
        </p>
        <code className="block font-[family-name:var(--font-geist-mono)] text-xs leading-relaxed text-foreground/70">
          {calc.formula}
        </code>
        <div className="my-3 h-px bg-primary/15" />
        <code className="block font-[family-name:var(--font-geist-mono)] text-[13px] leading-relaxed break-words text-foreground">
          {calc.substituted}
        </code>
        <div className="mt-4 flex items-baseline gap-2">
          <span className="text-xs text-muted-foreground">Final risk score</span>
          <span
            className={`font-[family-name:var(--font-display)] text-2xl font-bold ${riskTone(pct).text}`}
          >
            {pct}%
          </span>
        </div>
      </div>

      {/* Narrated derivation */}
      <div>
        <p className="mb-3 font-[family-name:var(--font-geist-mono)] text-[10px] tracking-widest text-muted-foreground uppercase">
          How we got to {pct}%, in plain English
        </p>
        <ol className="space-y-2.5">
          {calc.steps_human.map((line, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.06 * i, duration: 0.35 }}
              className="flex gap-3 rounded-lg bg-muted/25 px-3 py-2.5"
            >
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-primary/15 font-[family-name:var(--font-geist-mono)] text-[10px] font-bold text-primary">
                {i + 1}
              </span>
              <span className="text-xs leading-relaxed text-foreground/85">
                {line.replace(/^\d+\.\s*/, "")}
              </span>
            </motion.li>
          ))}
        </ol>
      </div>
    </div>
  );
}

/* ── Main section ─────────────────────────────────────────────────────── */

export function LiveDemo() {
  const [selected, setSelected] = useState<number | null>(null);
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [customQuery, setCustomQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [activeQuestion, setActiveQuestion] = useState("");

  const scoreQuestion = useCallback(async (question: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setActiveQuestion(question);
    try {
      const res = await fetch("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data: ScoreResult & { error?: string } = await res.json();

      if (!res.ok || data.error) {
        setError(data.error || `Request failed with HTTP ${res.status}.`);
        // Keep partial step data so the user can still see how far it got.
        if (data.steps?.length) setResult(data);
      } else {
        setResult(data);
      }
    } catch (e) {
      setError(
        `Could not reach the scoring API: ${e instanceof Error ? e.message : "unknown error"}.`,
      );
    }
    setLoading(false);
  }, []);

  const handleSelect = (index: number) => {
    setSelected(index);
    setCustomQuery("");
    scoreQuestion(demoQuestions[index]);
  };

  const handleCustomSubmit = () => {
    const q = customQuery.trim();
    if (q) {
      setSelected(-1);
      scoreQuestion(q);
    }
  };

  const hasScore = Boolean(result && !result.error && result.calculation);
  const riskPct = Math.round((result?.risk_score ?? 0) * 100);
  const tone = riskTone(riskPct);

  return (
    <section id="demo" className="relative py-24 sm:py-32">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/[0.03] to-transparent" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <span className="font-[family-name:var(--font-geist-mono)] text-sm font-semibold tracking-widest text-primary uppercase">
            Interactive Demo
          </span>
          <h2 className="font-[family-name:var(--font-display)] mt-4 text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            See <span className="gradient-text">every step</span> of the score
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Nothing is a black box. Run a query and watch the answer get split into
            claims, fact-checked one by one, and turned into a risk number you can
            re-derive yourself.
          </p>
        </motion.div>

        <div className="mt-16 grid gap-8 lg:grid-cols-12">
          {/* ── Query picker ── */}
          <div className="space-y-3 lg:col-span-4">
            <p className="font-[family-name:var(--font-geist-mono)] mb-4 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
              Select a query
            </p>
            {demoQuestions.map((q, i) => (
              <button
                key={i}
                onClick={() => handleSelect(i)}
                disabled={loading}
                className={`w-full rounded-xl border p-4 text-left transition-all duration-200 ${
                  selected === i
                    ? "border-primary/50 bg-primary/5 shadow-lg shadow-primary/10"
                    : "border-border bg-card/50 hover:border-border/80 hover:bg-card"
                } ${loading ? "cursor-not-allowed opacity-60" : ""}`}
              >
                <p className="text-sm font-medium">{q}</p>
              </button>
            ))}

            <div className="mt-4 space-y-2">
              <p className="font-[family-name:var(--font-geist-mono)] text-xs font-semibold tracking-widest text-muted-foreground uppercase">
                Or type your own
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customQuery}
                  onChange={(e) => setCustomQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCustomSubmit()}
                  placeholder="Ask anything…"
                  className="flex-1 rounded-xl border border-border bg-card/50 px-4 py-2.5 text-sm outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25"
                  disabled={loading}
                />
                <Button
                  size="sm"
                  onClick={handleCustomSubmit}
                  disabled={loading || !customQuery.trim()}
                  className="rounded-xl"
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* ── Results ── */}
          <div className="lg:col-span-8">
            <div className="gradient-border">
              <div className="glass-card rounded-2xl p-5 sm:p-7">
                {/* Terminal chrome */}
                <div className="mb-6 flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-red-500" />
                  <div className="h-3 w-3 rounded-full bg-yellow-500" />
                  <div className="h-3 w-3 rounded-full bg-green-500" />
                  <span className="font-[family-name:var(--font-geist-mono)] ml-2 text-xs text-muted-foreground">
                    halluciwatch-live
                  </span>
                  {result?.model_used && (
                    <Badge
                      variant="secondary"
                      className="font-[family-name:var(--font-geist-mono)] ml-auto text-xs"
                    >
                      {result.model_used}
                    </Badge>
                  )}
                </div>

                {/* Empty state */}
                {selected === null && !loading && !error && (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                      <Play className="h-8 w-8 text-primary/60" />
                    </div>
                    <p className="text-lg font-medium">Run your first query</p>
                    <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                      Pick a question on the left — the first five are designed to bait
                      the model into inventing facts.
                    </p>
                  </div>
                )}

                {/* Question echo */}
                {activeQuestion && (
                  <div className="mb-5 flex items-start gap-3">
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/20">
                      <Play className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <p className="rounded-xl rounded-tl-sm bg-muted/50 px-4 py-3 text-sm font-medium">
                      {activeQuestion}
                    </p>
                  </div>
                )}

                {/* Loading */}
                {loading && (
                  <div className="space-y-3 rounded-xl border border-border/50 bg-muted/20 p-5">
                    {[
                      "Generating an answer with Gemini…",
                      "Splitting it into atomic factual claims…",
                      "Fact-checking each claim independently…",
                      "Computing the weighted risk score…",
                    ].map((label, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0.25 }}
                        animate={{ opacity: [0.25, 1, 0.25] }}
                        transition={{ duration: 2, repeat: Infinity, delay: i * 0.45 }}
                        className="flex items-center gap-2.5 text-sm text-muted-foreground"
                      >
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                        {label}
                      </motion.div>
                    ))}
                  </div>
                )}

                {/* Error */}
                {error && !loading && (
                  <Reveal>
                    <div className="rounded-xl border border-red-500/25 bg-red-500/[0.06] p-4">
                      <div className="flex items-start gap-2.5">
                        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-red-300">
                            Scoring could not complete
                          </p>
                          <p className="mt-1.5 text-xs leading-relaxed break-words text-red-200/80">
                            {error}
                          </p>
                          {error.includes("429") || error.toLowerCase().includes("quota") ? (
                            <p className="mt-2.5 rounded-lg bg-black/25 p-2.5 text-xs text-amber-200/90">
                              Your Gemini API key has hit its free-tier limit. Wait for the
                              quota window to reset, or enable billing in Google AI Studio.
                              The pipeline deliberately reports this instead of guessing a
                              score.
                            </p>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </Reveal>
                )}

                {/* ── Full result ── */}
                {result && !loading && (
                  <div className="space-y-8">
                    {/* Answer */}
                    {result.response && (
                      <Reveal>
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-chart-2/20">
                            <span className="text-[10px] font-bold text-chart-2">AI</span>
                          </div>
                          <p className="rounded-xl rounded-tl-sm bg-muted/50 px-4 py-3 text-sm leading-relaxed">
                            {result.response}
                          </p>
                        </div>
                      </Reveal>
                    )}

                    {hasScore && result.calculation && (
                      <>
                        {/* Headline score */}
                        <Reveal delay={0.1}>
                          <div className="rounded-xl border border-border/60 bg-muted/25 p-5">
                            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                              <span className="font-[family-name:var(--font-geist-mono)] text-xs font-semibold tracking-widest text-muted-foreground uppercase">
                                Hallucination risk
                              </span>
                              <div className="flex items-center gap-3">
                                <span className="font-[family-name:var(--font-geist-mono)] text-xs text-muted-foreground">
                                  {result.total_latency_ms.toFixed(0)}ms
                                </span>
                                <span
                                  className={`font-[family-name:var(--font-display)] text-4xl font-bold ${tone.text}`}
                                >
                                  {riskPct}%
                                </span>
                              </div>
                            </div>

                            <div className="mb-4 h-2.5 w-full overflow-hidden rounded-full bg-muted">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.max(riskPct, 1.5)}%` }}
                                transition={{ duration: 1, ease: "easeOut" }}
                                className={`h-full rounded-full bg-gradient-to-r ${tone.bar}`}
                              />
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                              <Badge variant="secondary" className={tone.chip}>
                                <tone.Icon className="mr-1 h-3 w-3" />
                                {tone.label}
                              </Badge>
                              <Badge variant="secondary" className="text-xs">
                                {result.calculation.correct}/{result.calculation.total_claims} claims
                                verified · {result.confidence.toFixed(0)}% confidence
                              </Badge>
                            </div>
                          </div>
                        </Reveal>

                        {/* The math */}
                        <Reveal delay={0.18}>
                          <div>
                            <SectionHeading
                              icon={Calculator}
                              title="How this number was calculated"
                              hint="Step 4 is pure arithmetic — no model involved. Every input below is shown, so you can reproduce the score by hand."
                            />
                            <MathBreakdown
                              calc={result.calculation}
                              details={result.claim_details}
                            />
                          </div>
                        </Reveal>

                        {/* Flowchart */}
                        {result.mermaid && (
                          <Reveal delay={0.24}>
                            <div>
                              <SectionHeading
                                icon={GitBranch}
                                title="Flowchart of this run"
                                hint="Generated from this query's actual data — every claim node shows the verdict it received and the weight it contributed."
                              />
                              <MermaidDiagram chart={result.mermaid} />
                            </div>
                          </Reveal>
                        )}

                        {/* Pipeline steps */}
                        <Reveal delay={0.3}>
                          <div>
                            <SectionHeading
                              icon={Sparkles}
                              title="Pipeline steps"
                              hint="Expand any step to see its exact input, its raw output, and why it exists."
                            />
                            <div className="space-y-2.5">
                              {result.steps.map((s, i) => (
                                <StepCard key={s.step_number} step={s} index={i} />
                              ))}
                            </div>
                          </div>
                        </Reveal>

                        {/* Per-claim reasoning */}
                        {result.claim_details.length > 0 && (
                          <Reveal delay={0.36}>
                            <div>
                              <SectionHeading
                                icon={CheckCircle2}
                                title="Why each claim was judged that way"
                              />
                              <div className="space-y-2.5">
                                {result.claim_details.map((d) => {
                                  const s = verdictStyles[d.verdict] ?? verdictStyles.UNVERIFIABLE;
                                  const Icon = s.icon;
                                  return (
                                    <div key={d.index} className={`rounded-xl border p-3.5 ${s.ring}`}>
                                      <div className="flex items-start gap-2.5">
                                        <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${s.text}`} />
                                        <div className="min-w-0 flex-1">
                                          <p className="text-xs font-medium">{d.claim}</p>
                                          {d.reason && (
                                            <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                                              {d.reason}
                                            </p>
                                          )}
                                        </div>
                                        <span
                                          className={`shrink-0 rounded-md border px-2 py-0.5 font-[family-name:var(--font-geist-mono)] text-[9px] font-semibold ${s.chip}`}
                                        >
                                          {d.verdict}
                                        </span>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          </Reveal>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

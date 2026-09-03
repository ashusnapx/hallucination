"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  ArrowRight,
  Loader2,
  Radio,
  RotateCw,
  TerminalSquare,
} from "lucide-react";
import { ScoreError, score, type ScoreResult } from "@/lib/halluciwatch";
import { RiskDial } from "@/components/viz/risk-dial";
import { TokenHeatmap } from "@/components/viz/token-heatmap";
import { CascadeTrail } from "@/components/viz/cascade-trail";
import { ClusterBars } from "@/components/viz/cluster-bars";
import { SignalTable } from "@/components/viz/signal-table";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Presets chosen from the measured corpus, not invented. The first three are
 * questions llama3.2:3b answers confidently and wrongly; the last three it
 * either knows or honestly declines. Showing both is the point — a detector
 * that only ever fires looks broken.
 */
const PRESETS: { q: string; note: string }[] = [
  {
    q: "Where was the Fiddler in the musical's title?",
    note: "confidently wrong",
  },
  {
    q: "In music, who was Sweet and Innocent and Too Young?",
    note: "confidently wrong",
  },
  {
    q: "Who was the 14th person to walk on the surface of the Moon?",
    note: "unanswerable",
  },
  { q: "What is the capital of France?", note: "knows it" },
  { q: "Who wrote the play Romeo and Juliet?", note: "knows it" },
];

type Phase = "idle" | "running" | "done" | "error";

export function Demo() {
  const [question, setQuestion] = useState(PRESETS[0].q);
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [error, setError] = useState<{ message: string; kind: string } | null>(
    null,
  );
  const [elapsed, setElapsed] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const reduce = useReducedMotion();

  // A running clock while scoring. On a laptop this can take ten seconds when
  // the cascade escalates, and a spinner with no number feels broken.
  useEffect(() => {
    if (phase !== "running") return;
    const started = performance.now();
    const id = setInterval(
      () => setElapsed((performance.now() - started) / 1000),
      100,
    );
    return () => clearInterval(id);
  }, [phase]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const run = useCallback(async (q: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setPhase("running");
    setError(null);
    setElapsed(0);

    try {
      const data = await score(q, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setResult(data);
      setPhase("done");
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError({
        message:
          err instanceof ScoreError ? err.message : "Something went wrong.",
        kind: err instanceof ScoreError ? err.kind : "unknown",
      });
      setPhase("error");
    }
  }, []);

  return (
    <section className="pt-12 pb-(--spacing-section) sm:pt-16">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        {/* Question input ------------------------------------------------- */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (question.trim()) void run(question.trim());
          }}
          className=""
        >
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask the model anything…"
              aria-label="Question to score"
              className="min-w-0 flex-1 rounded-pill border border-rule bg-paper-raised px-5 py-3 text-[0.9375rem] text-ink outline-none transition-colors placeholder:text-ink-faint focus:border-rule-strong"
            />
            <Button
              type="submit"
              size="lg"
              disabled={phase === "running" || !question.trim()}
              className="sm:w-auto"
            >
              {phase === "running" ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Scoring {elapsed.toFixed(1)}s
                </>
              ) : (
                <>
                  Score it
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {PRESETS.map((p) => (
              <button
                key={p.q}
                type="button"
                disabled={phase === "running"}
                onClick={() => {
                  setQuestion(p.q);
                  void run(p.q);
                }}
                className={cn(
                  "group rounded-pill border px-3 py-1.5 text-left text-[0.75rem] transition-colors disabled:opacity-50",
                  question === p.q
                    ? "border-rule-strong bg-paper-sunken text-ink"
                    : "border-rule text-ink-muted hover:border-rule-strong hover:text-ink",
                )}
              >
                {p.q.length > 46 ? `${p.q.slice(0, 46)}…` : p.q}
                <span className="ml-1.5 font-mono text-[0.625rem] text-ink-faint">
                  {p.note}
                </span>
              </button>
            ))}
          </div>
        </form>

        {/* Output --------------------------------------------------------- */}
        <div className="mt-8" aria-live="polite" aria-atomic="false">
          <AnimatePresence mode="wait">
            {phase === "error" && error && (
              <motion.div
                key="error"
                initial={reduce ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-card border border-risk-danger/30 bg-risk-danger-wash p-5"
              >
                <div className="flex items-start gap-3">
                  <TerminalSquare className="mt-0.5 h-4 w-4 shrink-0 text-risk-danger" />
                  <div className="min-w-0">
                    <p className="text-[0.875rem] text-ink">{error.message}</p>
                    {error.kind === "backend-down" && <BackendDownHelp />}
                  </div>
                </div>
              </motion.div>
            )}

            {phase === "running" && (
              <motion.div
                key="running"
                initial={reduce ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <RunningSkeleton elapsed={elapsed} />
              </motion.div>
            )}

            {phase === "done" && result && (
              <motion.div
                key={result.question + result.risk}
                initial={reduce ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                className="space-y-4"
              >
                <Result
                  result={result}
                  onRerun={() => void run(result.question)}
                />
              </motion.div>
            )}

            {phase === "idle" && (
              <motion.div
                key="idle"
                initial={false}
                exit={{ opacity: 0 }}
                className="rounded-card border border-dashed border-rule px-6 py-14 text-center"
              >
                <Radio className="mx-auto h-5 w-5 text-ink-faint" aria-hidden />
                <p className="mt-3 text-[0.875rem] text-ink-muted">
                  Pick a question above, or write your own.
                </p>
                <p className="mt-1.5 font-mono text-[0.6875rem] text-ink-faint">
                  needs a local backend: ollama serve · cd backend &amp;&amp;
                  make serve
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}

/* ── Result ───────────────────────────────────────────────────────────────── */

function Result({
  result,
  onRerun,
}: {
  result: ScoreResult;
  onRerun: () => void;
}) {
  return (
    <>
      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-5 py-2.5">
          <span className="eyebrow">
            answer from{" "}
            <span className="font-mono normal-case text-ink-muted">
              {result.model}
            </span>
          </span>
          <button
            type="button"
            onClick={onRerun}
            className="inline-flex items-center gap-1.5 font-mono text-[0.6875rem] text-ink-faint transition-colors hover:text-ink"
          >
            <RotateCw className="h-3 w-3" />
            re-run
          </button>
        </div>
        <p className="px-5 py-4 text-[0.9375rem] leading-relaxed text-ink">
          {result.answer}
        </p>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <Panel className="flex items-center justify-center py-7">
          <RiskDial
            risk={result.risk}
            decision={result.decision}
            calibrated={result.calibrated}
          />
        </Panel>

        <div className="space-y-4">
          <Panel className="px-5 py-4">
            <h2 className="eyebrow mb-3.5">Cascade</h2>
            <CascadeTrail
              tiers={result.tiers_used}
              latency={result.latency_s}
              overhead={result.overhead_s}
            />
          </Panel>

          {result.top_factors.length > 0 && (
            <Panel className="px-5 py-4">
              <h2 className="eyebrow mb-2">Signals that moved the score</h2>
              <SignalTable factors={result.top_factors} />
            </Panel>
          )}
        </div>
      </div>

      {result.token_risk.length > 0 && (
        <Panel className="px-5 py-4">
          <h2 className="eyebrow mb-3">Per-token uncertainty</h2>
          <TokenHeatmap tokens={result.token_risk} />
        </Panel>
      )}

      {result.clusters.length > 0 && (
        <Panel className="px-5 py-4">
          <h2 className="eyebrow mb-3">Semantic clusters</h2>
          <ClusterBars clusters={result.clusters} />
        </Panel>
      )}

      {result.notes.length > 0 && (
        <div className="rounded-card border border-rule bg-paper-sunken px-5 py-3.5">
          {result.notes.map((note, i) => (
            <p
              key={i}
              className="font-mono text-[0.75rem] leading-relaxed text-ink-muted"
            >
              {note}
            </p>
          ))}
        </div>
      )}
    </>
  );
}

function Panel({
  children,
  className,
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-card border border-rule bg-paper-raised shadow-card",
        className,
      )}
    >
      {children}
    </div>
  );
}

function RunningSkeleton({ elapsed }: { elapsed: number }) {
  // Honest staging: the first phase really is generation, and sampling really
  // does start around a second in when the cascade escalates.
  const stage =
    elapsed < 1.2
      ? "generating an answer"
      : elapsed < 3
        ? "reading token probabilities"
        : "sampling again to compare meanings";

  return (
    <div className="space-y-4">
      <Panel className="px-5 py-4">
        <div className="flex items-center gap-2.5">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-ink-faint" />
          <span className="font-mono text-[0.75rem] text-ink-muted">
            {stage}…
          </span>
        </div>
        <div className="mt-3.5 space-y-2">
          <div className="sweep h-3 w-4/5 rounded bg-paper-sunken" />
          <div className="sweep h-3 w-3/5 rounded bg-paper-sunken" />
        </div>
      </Panel>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <Panel className="sweep h-56 bg-paper-sunken/40" />
        <Panel className="sweep h-56 bg-paper-sunken/40" />
      </div>
    </div>
  );
}

function BackendDownHelp() {
  return (
    <div className="mt-3 space-y-1 font-mono text-[0.75rem] text-ink-muted">
      <p className="text-ink-faint">start it with:</p>
      <p>ollama serve</p>
      <p>cd backend &amp;&amp; make serve</p>
    </div>
  );
}

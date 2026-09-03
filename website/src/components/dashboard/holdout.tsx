"use client";

import { AlertTriangle } from "lucide-react";
import { Panel } from "./panels";
import raw from "@/data/dashboard.json";

interface HoldoutSource {
  source: string;
  n: number;
  base_rate: number;
  n_correct: number;
  auroc: number | null;
}

interface Holdout {
  n: number;
  base_rate: number;
  n_correct: number;
  n_hallucinated: number;
  auroc: number;
  auprc: number;
  ece: number;
  by_source: HoldoutSource[];
  sources: Record<string, number>;
}

/**
 * Transfer to benchmarks the detector never trained on.
 *
 * The headline here is deliberately *not* the AUROC. TruthfulQA and SimpleQA
 * are adversarial by construction — TruthfulQA targets questions where humans
 * hold false beliefs, SimpleQA was filtered to questions frontier models get
 * wrong. A 3B model gets 4 of 227 right, so any ranking metric is separating a
 * handful of points from everything else and cannot be compared with the
 * in-domain number.
 *
 * Reporting 0.725 without that context would be the exact kind of flattering,
 * unfalsifiable number this project exists to argue against.
 */
export function HoldoutPanel() {
  const holdout = (raw as { holdout?: Holdout }).holdout;
  if (!holdout) return null;

  // Below this many minority-class examples, ranking metrics are noise.
  const MIN_MINORITY = 25;
  const unreliable = holdout.n_correct < MIN_MINORITY;
  const names = Object.keys(holdout.sources).join(" + ");

  return (
    <Panel
      title="Transfer to unseen benchmarks"
      hint={`Trained on TriviaQA and NQ-Open, scored on ${names} — named in the synopsis, and held out of training entirely.`}
    >
      {unreliable && (
        <div className="mb-5 flex gap-3 rounded-md border border-risk-caution/30 bg-risk-caution-wash px-3.5 py-3">
          <AlertTriangle
            className="mt-0.5 h-4 w-4 shrink-0 text-risk-caution"
            aria-hidden
          />
          <p className="text-[0.8125rem] leading-relaxed text-ink-muted">
            <span className="font-medium text-ink">
              These benchmarks cannot measure a detector at this model size.
            </span>{" "}
            The model answered{" "}
            <span className="font-mono text-ink">{holdout.n_correct}</span> of{" "}
            <span className="font-mono text-ink">{holdout.n}</span> questions
            correctly. Any ranking metric is separating {holdout.n_correct}{" "}
            points from {holdout.n_hallucinated}, so the AUROC below is unstable
            and must not be compared with the in-domain result. Both sets are
            adversarial by construction — they measure the <em>model</em>{" "}
            precisely and the <em>detector</em> barely at all.
          </p>
        </div>
      )}

      <dl className="grid grid-cols-2 gap-x-5 gap-y-3 sm:grid-cols-4">
        {[
          ["rows scored", `${holdout.n}`, false],
          ["answered correctly", `${holdout.n_correct}`, true],
          ["AUROC", holdout.auroc.toFixed(3), false],
          ["ECE", holdout.ece.toFixed(3), true],
        ].map(([k, v, warn]) => (
          <div key={k as string}>
            <dt className="eyebrow">{k}</dt>
            <dd
              className="mt-1 font-mono text-[1.125rem]"
              style={{
                color: warn ? "var(--risk-caution)" : "var(--ink)",
              }}
            >
              {v}
            </dd>
          </div>
        ))}
      </dl>

      <table className="mt-5 w-full text-left text-[0.8125rem]">
        <thead>
          <tr className="border-b border-rule">
            <th className="pb-2 font-medium text-ink-faint">dataset</th>
            <th className="pb-2 text-right font-medium text-ink-faint">n</th>
            <th className="pb-2 text-right font-medium text-ink-faint">
              correct
            </th>
            <th className="pb-2 text-right font-medium text-ink-faint">
              AUROC
            </th>
          </tr>
        </thead>
        <tbody>
          {holdout.by_source.map((s) => (
            <tr key={s.source} className="border-b border-rule last:border-0">
              <td className="py-2 font-mono text-ink-muted">{s.source}</td>
              <td className="py-2 text-right font-mono text-ink-faint">
                {s.n}
              </td>
              <td className="py-2 text-right font-mono text-risk-caution">
                {s.n_correct}
              </td>
              <td className="py-2 text-right font-mono text-ink-faint">
                {s.auroc === null ? "n/a" : `${s.auroc.toFixed(3)}*`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mt-3 text-[0.75rem] leading-relaxed text-ink-faint">
        * Starred values are computed but not meaningful at this class balance.
        The honest conclusion is about the generator, not the detector:{" "}
        <span className="text-ink-muted">
          a 3B model is not able to answer adversarial factuality benchmarks at
          all
        </span>
        , which is itself a result — and the reason the main study uses TriviaQA
        and NQ-Open, where the model gets roughly half right and a detector has
        something to separate.
      </p>
    </Panel>
  );
}

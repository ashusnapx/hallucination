"use client";

import { XYChart } from "@/components/viz/xy-chart";
import { ConfusionMatrix } from "@/components/viz/confusion-matrix";
import { BarList } from "@/components/viz/bar-list";
import { prettyFeature, tierOfFeature } from "@/lib/halluciwatch";
import { cn } from "@/lib/utils";
import data from "@/data/dashboard.json";

export function Panel({
  title,
  hint,
  children,
  className,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-card border border-rule bg-paper-raised p-5 shadow-card",
        className,
      )}
    >
      <h3 className="eyebrow">{title}</h3>
      {hint && (
        <p className="mt-1.5 text-[0.75rem] leading-relaxed text-ink-faint">
          {hint}
        </p>
      )}
      <div className="mt-4">{children}</div>
    </section>
  );
}

const DIAGONAL = [
  { x: 0, y: 0 },
  { x: 1, y: 1 },
];

export function RocPanel() {
  return (
    <Panel
      title="ROC curve"
      hint={`AUROC ${data.headline.auroc} [${data.headline.auroc_ci[0]}, ${data.headline.auroc_ci[1]}]. The dashed line is chance.`}
    >
      <XYChart
        ariaLabel={`Receiver operating characteristic curve, area under curve ${data.headline.auroc}`}
        series={[
          {
            points: DIAGONAL,
            dashed: true,
            label: "chance",
            color: "var(--ink-faint)",
          },
          { points: data.roc, area: true, label: "detector" },
        ]}
        xLabel="false positive rate"
        yLabel="true positive rate"
      />
    </Panel>
  );
}

export function PrPanel() {
  const base = data.headline.base_rate;
  return (
    <Panel
      title="Precision–recall"
      hint={`AUPRC ${data.headline.auprc}. The dashed line is the ${(base * 100).toFixed(1)}% base rate a coin-flip would achieve.`}
    >
      <XYChart
        ariaLabel={`Precision recall curve, average precision ${data.headline.auprc}`}
        series={[
          {
            points: [
              { x: 0, y: base },
              { x: 1, y: base },
            ],
            dashed: true,
            label: "base rate",
            color: "var(--ink-faint)",
          },
          { points: data.pr, area: true, label: "detector" },
        ]}
        xLabel="recall"
        yLabel="precision"
      />
    </Panel>
  );
}

export function ReliabilityPanel() {
  return (
    <Panel
      title="Calibration"
      hint={`ECE ${data.headline.ece}. Points on the diagonal mean a score of 0.30 really is wrong about 30% of the time.`}
    >
      <XYChart
        ariaLabel={`Reliability diagram, expected calibration error ${data.headline.ece}`}
        series={[
          {
            points: DIAGONAL,
            dashed: true,
            label: "perfect",
            color: "var(--ink-faint)",
          },
          {
            points: data.reliability.map((r) => ({
              x: r.predicted,
              y: r.observed,
            })),
            label: "observed",
            dots: true,
          },
          {
            points: data.reliability.map((r) => ({
              x: r.predicted,
              y: r.observed,
            })),
          },
        ]}
        xLabel="predicted probability"
        yLabel="observed frequency"
      />
    </Panel>
  );
}

export function RiskCoveragePanel() {
  return (
    <Panel
      title="Risk–coverage"
      hint={`Auto-accept the lowest-risk answers and this is the error you inherit. Accepting everything gives the ${(data.headline.base_rate * 100).toFixed(1)}% base rate.`}
    >
      <XYChart
        ariaLabel="Risk coverage curve: error rate among accepted answers against coverage"
        series={[
          {
            points: [
              { x: 0, y: data.headline.base_rate },
              { x: 1, y: data.headline.base_rate },
            ],
            dashed: true,
            label: "no detector",
            color: "var(--ink-faint)",
          },
          {
            points: data.risk_coverage.map((r) => ({
              x: r.coverage,
              y: r.error,
            })),
            label: "with detector",
            color: "var(--risk-safe)",
            area: true,
          },
        ]}
        xLabel="coverage"
        yLabel="error among accepted"
        yDomain={[0, 0.8]}
      />
    </Panel>
  );
}

export function ScoreDistributionPanel() {
  const max = Math.max(
    ...data.score_histogram.map((b) => Math.max(b.correct, b.hallucinated)),
    1,
  );
  return (
    <Panel
      title="Score distribution"
      hint="Where the two classes land. Overlap in the middle is the part the detector cannot separate — that band is what the cascade escalates."
    >
      <div className="flex h-40 items-end gap-[3px]">
        {data.score_histogram.map((b) => (
          <div
            key={b.bin}
            className="flex flex-1 flex-col justify-end gap-[2px]"
            title={`risk ${b.bin}: ${b.correct} correct, ${b.hallucinated} hallucinated`}
          >
            <div
              className="w-full rounded-sm bg-risk-danger/70"
              style={{ height: `${(b.hallucinated / max) * 60}%` }}
            />
            <div
              className="w-full rounded-sm bg-risk-safe/70"
              style={{ height: `${(b.correct / max) * 60}%` }}
            />
          </div>
        ))}
      </div>
      <div className="mt-2 flex items-center justify-between font-mono text-[0.625rem] text-ink-faint">
        <span>risk 0.0</span>
        <span className="flex gap-3">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm bg-risk-safe/70" /> correct
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm bg-risk-danger/70" />{" "}
            hallucinated
          </span>
        </span>
        <span>1.0</span>
      </div>
    </Panel>
  );
}

export function ConfusionPanel() {
  const at50 =
    data.confusion.find((c) => c.threshold === 0.5) ?? data.confusion[0];
  return (
    <Panel
      title="Confusion matrix"
      hint="At the default 0.5 threshold. Recall is deliberately higher than precision — for a guardrail, a missed hallucination costs more than a false alarm."
    >
      <ConfusionMatrix data={at50} />
    </Panel>
  );
}

export function TierPanel() {
  return (
    <Panel
      title="What each tier buys"
      hint="AUROC for each signal family alone, with its measured cost per query."
    >
      <table className="w-full text-left text-[0.8125rem]">
        <thead>
          <tr className="border-b border-rule">
            <th className="pb-2 font-medium text-ink-faint">tiers</th>
            <th className="pb-2 text-right font-medium text-ink-faint">
              feats
            </th>
            <th className="pb-2 text-right font-medium text-ink-faint">
              AUROC
            </th>
            <th className="pb-2 text-right font-medium text-ink-faint">cost</th>
          </tr>
        </thead>
        <tbody>
          {data.per_tier.map((t) => {
            const best = t.label === "token";
            return (
              <tr key={t.label} className="border-b border-rule last:border-0">
                <td
                  className={cn(
                    "py-2 font-mono",
                    best ? "text-ink" : "text-ink-muted",
                  )}
                >
                  {t.label}
                  {best && (
                    <span className="ml-2 rounded-pill border border-rule px-1.5 py-0.5 text-[0.5625rem] text-ink-faint">
                      best value
                    </span>
                  )}
                </td>
                <td className="py-2 text-right font-mono text-ink-faint">
                  {t.features}
                </td>
                <td className="py-2 text-right font-mono text-ink">
                  {t.auroc.toFixed(3)}
                </td>
                <td className="py-2 text-right font-mono text-ink-muted">
                  {t.cost_s.toFixed(2)}s
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}

export function FeaturePanel() {
  return (
    <Panel
      title="Strongest single features"
      hint="AUROC each feature achieves alone. The top one beats the full 36-feature model — on this many rows the ensemble is fitting noise."
    >
      <BarList
        baseline={0.5}
        max={0.82}
        items={data.top_features.slice(0, 10).map((f) => ({
          label: prettyFeature(f.feature),
          value: f.auroc,
          hint: tierOfFeature(f.feature),
        }))}
      />
    </Panel>
  );
}

export function ImportancePanel() {
  if (!data.importances.length) return null;
  return (
    <Panel
      title="Model feature importance"
      hint="Gain from the trained XGBoost. Note how little it agrees with the single-feature ranking beside it."
    >
      <BarList
        items={data.importances.slice(0, 10).map((f) => ({
          label: prettyFeature(f.feature),
          value: f.gain,
          hint: tierOfFeature(f.feature),
        }))}
        format={(v) => v.toFixed(3)}
      />
    </Panel>
  );
}

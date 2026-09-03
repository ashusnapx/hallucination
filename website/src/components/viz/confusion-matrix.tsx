"use client";

import { cn } from "@/lib/utils";

export interface Confusion {
  threshold: number;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
}

/**
 * Confusion matrix with the derived rates spelled out.
 *
 * Cell shading is scaled to the largest cell so the diagonal reads at a glance,
 * but every cell also carries its raw count — a heat-map alone hides whether a
 * light cell means "few" or "none", and on a 510-row study that difference
 * matters.
 */
export function ConfusionMatrix({
  data,
  className,
}: {
  data: Confusion;
  className?: string;
}) {
  const { tp, fp, tn, fn } = data;
  const max = Math.max(tp, fp, tn, fn, 1);
  const total = tp + fp + tn + fn;

  const precision = tp + fp > 0 ? tp / (tp + fp) : 0;
  const recall = tp + fn > 0 ? tp / (tp + fn) : 0;
  const specificity = tn + fp > 0 ? tn / (tn + fp) : 0;
  const f1 =
    precision + recall > 0
      ? (2 * precision * recall) / (precision + recall)
      : 0;

  const cell = (value: number, good: boolean, label: string) => (
    <div
      className="relative flex flex-col items-center justify-center rounded-md border border-rule px-3 py-4"
      style={{
        background: `color-mix(in oklab, var(--risk-${good ? "safe" : "danger"}) ${Math.round((value / max) * 22)}%, transparent)`,
      }}
    >
      <span className="font-mono text-[1.25rem] leading-none text-ink">
        {value}
      </span>
      <span className="mt-1 font-mono text-[0.5625rem] text-ink-faint">
        {label}
      </span>
    </div>
  );

  return (
    <div className={cn("space-y-3", className)}>
      <div className="grid grid-cols-[auto_1fr_1fr] gap-1.5">
        <div />
        <div className="pb-1 text-center font-mono text-[0.5625rem] text-ink-faint">
          predicted correct
        </div>
        <div className="pb-1 text-center font-mono text-[0.5625rem] text-ink-faint">
          predicted hallucinated
        </div>

        <div className="flex items-center pr-1.5 text-right font-mono text-[0.5625rem] text-ink-faint">
          actually
          <br />
          correct
        </div>
        {cell(tn, true, "true neg")}
        {cell(fp, false, "false pos")}

        <div className="flex items-center pr-1.5 text-right font-mono text-[0.5625rem] text-ink-faint">
          actually
          <br />
          halluc.
        </div>
        {cell(fn, false, "false neg")}
        {cell(tp, true, "true pos")}
      </div>

      <dl className="grid grid-cols-2 gap-x-5 gap-y-1.5 border-t border-rule pt-3 sm:grid-cols-4">
        {[
          ["Precision", precision],
          ["Recall", recall],
          ["Specificity", specificity],
          ["F1", f1],
        ].map(([label, v]) => (
          <div key={label as string}>
            <dt className="font-mono text-[0.5625rem] text-ink-faint uppercase tracking-wide">
              {label}
            </dt>
            <dd className="mt-0.5 font-mono text-[0.875rem] text-ink">
              {(v as number).toFixed(3)}
            </dd>
          </div>
        ))}
      </dl>

      <p className="font-mono text-[0.625rem] text-ink-faint">
        n={total} at threshold {data.threshold}
      </p>
    </div>
  );
}

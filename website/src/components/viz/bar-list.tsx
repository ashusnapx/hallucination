"use client";

import { cn } from "@/lib/utils";

/**
 * A ranked horizontal bar list — used for feature importance and per-feature
 * AUROC, where the label is long and the ordering is the message.
 *
 * `baseline` draws a reference line (0.5 for AUROC, i.e. chance), because a bar
 * chart of AUROC starting at zero makes every feature look strong.
 */
export function BarList({
  items,
  max,
  baseline,
  format = (v: number) => v.toFixed(3),
  className,
}: {
  items: { label: string; value: number; hint?: string }[];
  max?: number;
  baseline?: number;
  format?: (v: number) => string;
  className?: string;
}) {
  const hi = max ?? Math.max(...items.map((i) => i.value), 0.0001);
  const lo = baseline ?? 0;
  const span = Math.max(hi - lo, 1e-6);

  return (
    <ul className={cn("space-y-1.5", className)}>
      {items.map((item) => {
        const pct = Math.max(0, Math.min(1, (item.value - lo) / span)) * 100;
        return (
          <li
            key={item.label}
            className="grid grid-cols-[1fr_auto] items-center gap-3"
          >
            <div className="min-w-0">
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate font-mono text-[0.6875rem] text-ink-muted">
                  {item.label}
                </span>
                {item.hint && (
                  <span className="shrink-0 font-mono text-[0.5625rem] text-ink-faint">
                    {item.hint}
                  </span>
                )}
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-paper-sunken">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
            <span className="w-12 text-right font-mono text-[0.75rem] text-ink">
              {format(item.value)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

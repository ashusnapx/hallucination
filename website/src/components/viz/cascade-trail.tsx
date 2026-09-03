"use client";

import { Check, Minus } from "lucide-react";
import { TIER_META, type Tier } from "@/lib/halluciwatch";
import { cn } from "@/lib/utils";

const ORDER: Tier[] = ["surface", "token", "sampling"];

/**
 * Which tiers actually ran on this request.
 *
 * The point of the cascade is that skipping a stage is the *good* outcome, so
 * a skipped tier is drawn as deliberately dimmed-and-dashed rather than as a
 * failure. The connector between stages carries the same state, which is what
 * makes "it stopped here" legible at a glance.
 */
export function CascadeTrail({
  tiers,
  latency,
  overhead,
  className,
}: {
  tiers: Tier[];
  latency: number;
  overhead: number;
  className?: string;
}) {
  const escalated = tiers.includes("sampling");

  return (
    <div className={cn("space-y-3.5", className)}>
      <ol className="flex items-stretch gap-0">
        {ORDER.map((tier, i) => {
          const ran = tiers.includes(tier);
          const meta = TIER_META[tier];
          const nextRan = i < ORDER.length - 1 && tiers.includes(ORDER[i + 1]);

          return (
            <li key={tier} className="flex min-w-0 flex-1 items-stretch">
              <div
                className={cn(
                  "min-w-0 flex-1 rounded-card border px-3 py-2.5 transition-colors",
                  ran
                    ? "border-rule-strong bg-paper-raised"
                    : "border-dashed border-rule bg-transparent",
                )}
              >
                <div className="flex items-center gap-1.5">
                  {ran ? (
                    <Check
                      className="h-3 w-3 shrink-0 text-risk-safe"
                      aria-hidden
                    />
                  ) : (
                    <Minus
                      className="h-3 w-3 shrink-0 text-ink-faint"
                      aria-hidden
                    />
                  )}
                  <span
                    className={cn(
                      "truncate text-[0.8125rem] font-medium",
                      ran ? "text-ink" : "text-ink-faint",
                    )}
                  >
                    {meta.label}
                  </span>
                </div>
                <span
                  className={cn(
                    "mt-0.5 block font-mono text-[0.6875rem]",
                    ran ? "text-ink-muted" : "text-ink-faint",
                  )}
                >
                  {ran ? meta.cost : "skipped"}
                </span>
              </div>

              {i < ORDER.length - 1 && (
                <div
                  className="mx-1 w-3 shrink-0 self-center border-t"
                  style={{
                    borderColor: nextRan ? "var(--rule-strong)" : "var(--rule)",
                    borderTopStyle: nextRan ? "solid" : "dashed",
                  }}
                  aria-hidden
                />
              )}
            </li>
          );
        })}
      </ol>

      <p className="text-[0.8125rem] leading-snug text-ink-muted">
        {escalated
          ? "The cheap signals were ambiguous, so it sampled the model again and clustered the answers."
          : "The cheap signals were decisive. Sampling was skipped, saving several generations."}
      </p>

      <dl className="flex gap-5 border-t border-rule pt-3 font-mono text-[0.6875rem]">
        <div>
          <dt className="text-ink-faint">total</dt>
          <dd className="mt-0.5 text-ink">{latency.toFixed(2)}s</dd>
        </div>
        <div>
          <dt className="text-ink-faint">scoring overhead</dt>
          <dd className="mt-0.5 text-ink">{overhead.toFixed(2)}s</dd>
        </div>
        <div>
          <dt className="text-ink-faint">share of total</dt>
          <dd className="mt-0.5 text-ink">
            {latency > 0 ? `${((overhead / latency) * 100).toFixed(0)}%` : "—"}
          </dd>
        </div>
      </dl>
    </div>
  );
}

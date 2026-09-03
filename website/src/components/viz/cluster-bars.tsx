"use client";

import { cn } from "@/lib/utils";

/**
 * Semantic clusters: the distinct *meanings* the model produced when asked the
 * same question several times.
 *
 * Proportion bars rather than a pie or treemap. With 2–6 groups and long text
 * labels, a horizontal bar per cluster is the only form that keeps the label
 * readable, and reading down the left edge tells the story on its own: one long
 * bar means the model is consistent, several short ones mean it is guessing.
 */
export function ClusterBars({
  clusters,
  className,
}: {
  clusters: string[][];
  className?: string;
}) {
  if (clusters.length === 0) return null;

  const total = clusters.reduce((n, c) => n + c.length, 0);
  const ordered = [...clusters].sort((a, b) => b.length - a.length);
  const unanimous = ordered.length === 1;

  return (
    <div className={cn("space-y-3", className)}>
      <p className="text-[0.8125rem] text-ink-muted">
        Asked <span className="font-mono text-ink">{total}×</span> —{" "}
        {unanimous ? (
          <>the model said the same thing every time.</>
        ) : (
          <>
            <span className="font-mono text-ink">{ordered.length}</span>{" "}
            different meanings came back.
          </>
        )}
      </p>

      <ul className="space-y-1.5">
        {ordered.slice(0, 6).map((cluster, i) => {
          const share = cluster.length / total;
          return (
            <li
              key={i}
              className="relative overflow-hidden rounded-md border border-rule bg-paper-raised"
            >
              <div
                className="absolute inset-y-0 left-0"
                style={{
                  width: `${share * 100}%`,
                  background:
                    i === 0
                      ? "var(--risk-safe-wash)"
                      : "var(--risk-caution-wash)",
                }}
                aria-hidden
              />
              <div className="relative flex items-center gap-3 px-3 py-2">
                <span className="min-w-0 flex-1 truncate text-[0.8125rem] text-ink">
                  {cluster[0]}
                </span>
                <span className="shrink-0 font-mono text-[0.6875rem] text-ink-muted">
                  ×{cluster.length}
                </span>
              </div>
            </li>
          );
        })}
      </ul>

      {!unanimous && (
        <p className="text-[0.75rem] leading-snug text-ink-faint">
          This is semantic entropy. Disagreement across independent samples is
          what catches a confidently wrong answer that token probabilities miss.
        </p>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { DELIVERABLES, STATUS_META, type Status } from "@/lib/proposal";
import { cn } from "@/lib/utils";

const ORDER: Status[] = ["met", "partial", "changed", "missed"];

/**
 * The project scored against its own Phase-1 proposal.
 *
 * This is the first thing on the dashboard because it is the question a
 * reviewer actually has: did it do what it said it would? Two targets were
 * missed and they are labelled missed, in the same type as everything else —
 * a scorecard that only shows green is not a scorecard.
 */
export function Scorecard() {
  const [open, setOpen] = useState<string | null>(null);

  const counts = ORDER.map((s) => ({
    status: s,
    n: DELIVERABLES.filter((d) => d.status === s).length,
  }));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {counts.map(({ status, n }) => {
          const meta = STATUS_META[status];
          return (
            <span
              key={status}
              className="inline-flex items-center gap-2 rounded-pill border px-3 py-1.5 text-[0.75rem]"
              style={{
                borderColor: `var(--risk-${meta.token})`,
                background: `var(--risk-${meta.token}-wash)`,
                color: `var(--risk-${meta.token})`,
              }}
            >
              <span className="font-mono font-medium">{n}</span>
              {meta.label}
            </span>
          );
        })}
      </div>

      <div className="overflow-hidden rounded-card border border-rule">
        <ul>
          {DELIVERABLES.map((d) => {
            const meta = STATUS_META[d.status];
            const isOpen = open === d.id;
            return (
              <li key={d.id} className="border-b border-rule last:border-0">
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : d.id)}
                  aria-expanded={isOpen}
                  className="flex w-full items-start gap-4 px-4 py-3.5 text-left transition-colors hover:bg-paper-sunken sm:px-5"
                >
                  <span
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                    style={{ background: `var(--risk-${meta.token})` }}
                    aria-hidden
                  />

                  <span className="grid min-w-0 flex-1 gap-1 sm:grid-cols-[1.1fr_1fr_1fr] sm:gap-4">
                    <span className="min-w-0 text-[0.875rem] font-medium text-ink">
                      {d.promised}
                    </span>
                    <span className="min-w-0 font-mono text-[0.75rem] text-ink-faint">
                      <span className="sm:hidden">target: </span>
                      {d.target}
                    </span>
                    <span className="min-w-0 font-mono text-[0.75rem] text-ink-muted">
                      <span className="sm:hidden">actual: </span>
                      {d.actual}
                    </span>
                  </span>

                  <span
                    className="shrink-0 font-mono text-[0.6875rem]"
                    style={{ color: `var(--risk-${meta.token})` }}
                  >
                    {meta.label}
                  </span>
                  <ChevronDown
                    className={cn(
                      "mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-faint transition-transform duration-200",
                      isOpen && "rotate-180",
                    )}
                    aria-hidden
                  />
                </button>

                {isOpen && (
                  <p className="border-t border-rule bg-paper-sunken px-4 py-3.5 text-[0.8125rem] leading-relaxed text-ink-muted sm:px-5 sm:pl-11">
                    {d.note}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      <p className="text-[0.75rem] leading-relaxed text-ink-faint">
        Targets are transcribed from the submitted Phase-1 synopsis and slide
        deck. Click any row for why it landed where it did.
      </p>
    </div>
  );
}

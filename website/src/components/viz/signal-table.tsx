"use client";

import { prettyFeature, tierOfFeature, formatValue } from "@/lib/halluciwatch";
import { cn } from "@/lib/utils";

const TIER_DOT: Record<string, string> = {
  token: "var(--risk-caution)",
  sampling: "var(--accent)",
  surface: "var(--ink-faint)",
  verify: "var(--risk-neutral)",
};

/**
 * The features that actually drove this score, ranked by the trained model's
 * gain — and filtered by the backend to features that were genuinely computed
 * on this request, so a skipped tier never appears here at 0.000.
 */
export function SignalTable({
  factors,
  className,
}: {
  factors: [string, number][];
  className?: string;
}) {
  if (!factors.length) return null;

  return (
    <table className={cn("w-full text-[0.8125rem]", className)}>
      <caption className="sr-only">Signals that drove the risk score</caption>
      <tbody>
        {factors.slice(0, 6).map(([name, value]) => (
          <tr key={name} className="border-b border-rule last:border-0">
            <td className="py-1.5 pr-3">
              <span className="flex items-center gap-2">
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: TIER_DOT[tierOfFeature(name)] }}
                  aria-hidden
                />
                <span className="text-ink-muted">{prettyFeature(name)}</span>
              </span>
            </td>
            <td className="py-1.5 text-right font-mono text-ink">
              {formatValue(value)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

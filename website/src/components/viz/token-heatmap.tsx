"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

/**
 * The model's own uncertainty, painted onto the words it chose.
 *
 * This is the site's signature visual and the one thing no black-box tool can
 * show: at every token the model had a probability distribution over what to
 * say next, and this is the shape of it.
 *
 * Two decisions worth stating:
 *
 * - The tint is applied as a **background wash whose alpha scales with
 *   uncertainty**, not as a text colour. Recolouring text destroys contrast at
 *   exactly the moment you want people to read it; a wash keeps the ink at full
 *   contrast and puts the signal behind it.
 * - The ramp runs neutral → caution → danger rather than a rainbow. A
 *   perceptually sequential ramp reads as "more of one thing", which is what
 *   uncertainty is. A diverging or categorical scale would imply kinds.
 */
export function TokenHeatmap({
  tokens,
  className,
}: {
  tokens: [string, number][];
  className?: string;
}) {
  const [hovered, setHovered] = useState<number | null>(null);

  if (!tokens.length) return null;

  const peak = tokens.reduce(
    (best, [, v], i) => (v > tokens[best][1] ? i : best),
    0,
  );

  return (
    <div className={cn("space-y-3", className)}>
      <p
        className="font-mono text-[0.9375rem] leading-[2.1]"
        // The heat-map is decorative relative to the answer text, which is
        // already announced above; announcing every token would be noise.
        aria-hidden
      >
        {tokens.map(([token, risk], i) => {
          const display = token.replace(/\n/g, "↵");
          const isSpaceOnly = token.trim() === "";
          return (
            <span
              key={i}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              className={cn(
                "relative rounded-[3px] transition-[background-color] duration-150",
                !isSpaceOnly && "cursor-default",
                hovered === i && "ring-1 ring-rule-strong",
              )}
              style={{ backgroundColor: tint(risk) }}
            >
              {display}
              {hovered === i && !isSpaceOnly && (
                <span className="pointer-events-none absolute -top-7 left-1/2 z-20 -translate-x-1/2 whitespace-nowrap rounded-md border border-rule bg-paper-raised px-1.5 py-0.5 font-mono text-[0.625rem] text-ink shadow-card">
                  {risk.toFixed(3)}
                </span>
              )}
            </span>
          );
        })}
      </p>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-rule pt-3">
        <Legend />
        <span className="font-mono text-[0.6875rem] text-ink-faint">
          peak {tokens[peak][1].toFixed(2)} at{" "}
          <span className="text-ink-muted">
            “{tokens[peak][0].trim() || "␣"}”
          </span>
        </span>
      </div>
    </div>
  );
}

/** alpha ramps with uncertainty; hue shifts caution → danger past the midpoint. */
function tint(risk: number): string {
  const r = Math.min(Math.max(risk, 0), 1);
  if (r < 0.12) return "transparent";
  if (r < 0.5) {
    return `color-mix(in oklab, var(--risk-caution) ${Math.round(r * 46)}%, transparent)`;
  }
  return `color-mix(in oklab, var(--risk-danger) ${Math.round(18 + r * 34)}%, transparent)`;
}

function Legend() {
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[0.6875rem] text-ink-faint">certain</span>
      <div className="flex h-2 w-24 overflow-hidden rounded-full">
        {Array.from({ length: 12 }, (_, i) => (
          <div
            key={i}
            className="flex-1"
            style={{ backgroundColor: tint((i + 0.5) / 12) || "var(--rule)" }}
          />
        ))}
      </div>
      <span className="font-mono text-[0.6875rem] text-ink-faint">
        uncertain
      </span>
    </div>
  );
}

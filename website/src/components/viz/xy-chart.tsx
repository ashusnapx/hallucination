"use client";

import { useId, useState } from "react";
import { cn } from "@/lib/utils";

export interface Series {
  points: { x: number; y: number }[];
  color?: string;
  label?: string;
  /** Draw as a dashed reference line (chance diagonal, perfect calibration). */
  dashed?: boolean;
  /** Fill the area under the curve. */
  area?: boolean;
  /** Render as discrete markers rather than a path. */
  dots?: boolean;
}

/**
 * One small SVG chart used for every curve on the dashboard: ROC, PR,
 * risk-coverage and the reliability diagram.
 *
 * Written by hand rather than pulled from a charting library. These are four
 * near-identical 0–1 line charts with a reference diagonal; Recharts would add
 * ~50kB and still need overriding to match the type and colour system.
 *
 * A crosshair reads the nearest point on hover, because on a ROC curve the
 * interesting question is always "what is TPR at this FPR" and a static plot
 * cannot answer it.
 */
export function XYChart({
  series,
  xLabel,
  yLabel,
  xDomain = [0, 1],
  yDomain = [0, 1],
  height = 220,
  formatX = (v: number) => v.toFixed(2),
  formatY = (v: number) => v.toFixed(2),
  className,
  ariaLabel,
}: {
  series: Series[];
  xLabel: string;
  yLabel: string;
  xDomain?: [number, number];
  yDomain?: [number, number];
  height?: number;
  formatX?: (v: number) => string;
  formatY?: (v: number) => string;
  className?: string;
  ariaLabel: string;
}) {
  const clip = useId();
  const [hover, setHover] = useState<{ x: number; y: number } | null>(null);

  const W = 400;
  const H = height;
  const M = { top: 12, right: 14, bottom: 32, left: 52 };
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;

  const sx = (v: number) =>
    M.left + ((v - xDomain[0]) / (xDomain[1] - xDomain[0])) * iw;
  const sy = (v: number) =>
    M.top + ih - ((v - yDomain[0]) / (yDomain[1] - yDomain[0])) * ih;

  const primary = series.find((s) => !s.dashed) ?? series[0];

  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    if (!primary?.points.length) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    // Nearest point by x in screen space, so the readout always lands on real data.
    let best = primary.points[0];
    let bestD = Infinity;
    for (const p of primary.points) {
      const d = Math.abs(sx(p.x) - px);
      if (d < bestD) {
        bestD = d;
        best = p;
      }
    }
    setHover(best);
  }

  const ticks = [0, 0.25, 0.5, 0.75, 1].map(
    (t) => xDomain[0] + t * (xDomain[1] - xDomain[0]),
  );
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map(
    (t) => yDomain[0] + t * (yDomain[1] - yDomain[0]),
  );

  return (
    <figure className={cn("w-full", className)}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full touch-none"
        role="img"
        aria-label={ariaLabel}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <clipPath id={clip}>
            <rect x={M.left} y={M.top} width={iw} height={ih} />
          </clipPath>
        </defs>

        {yTicks.map((t) => (
          <g key={`y${t}`}>
            <line
              x1={M.left}
              x2={W - M.right}
              y1={sy(t)}
              y2={sy(t)}
              stroke="var(--rule)"
              strokeDasharray="2 5"
            />
            <text
              x={M.left - 8}
              y={sy(t)}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-[var(--ink-faint)] font-mono text-[9px]"
            >
              {formatY(t)}
            </text>
          </g>
        ))}

        {ticks.map((t) => (
          <text
            key={`x${t}`}
            x={sx(t)}
            y={H - M.bottom + 14}
            textAnchor="middle"
            className="fill-[var(--ink-faint)] font-mono text-[9px]"
          >
            {formatX(t)}
          </text>
        ))}

        <g clipPath={`url(#${clip})`}>
          {series.map((s, i) => {
            const color = s.color ?? "var(--accent)";
            const d = s.points
              .map((p, j) => `${j === 0 ? "M" : "L"} ${sx(p.x)} ${sy(p.y)}`)
              .join(" ");

            if (s.dots) {
              return (
                <g key={i}>
                  {s.points.map((p, j) => (
                    <circle
                      key={j}
                      cx={sx(p.x)}
                      cy={sy(p.y)}
                      r={3}
                      fill={color}
                      opacity={0.85}
                    />
                  ))}
                </g>
              );
            }
            return (
              <g key={i}>
                {s.area && (
                  <path
                    d={`${d} L ${sx(s.points[s.points.length - 1].x)} ${sy(yDomain[0])} L ${sx(s.points[0].x)} ${sy(yDomain[0])} Z`}
                    fill={color}
                    opacity={0.1}
                  />
                )}
                <path
                  d={d}
                  fill="none"
                  stroke={color}
                  strokeWidth={s.dashed ? 1 : 2}
                  strokeDasharray={s.dashed ? "4 4" : undefined}
                  opacity={s.dashed ? 0.5 : 1}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              </g>
            );
          })}

          {hover && (
            <g>
              <line
                x1={sx(hover.x)}
                x2={sx(hover.x)}
                y1={M.top}
                y2={M.top + ih}
                stroke="var(--ink-faint)"
                strokeDasharray="3 3"
              />
              <circle
                cx={sx(hover.x)}
                cy={sy(hover.y)}
                r={4}
                fill="var(--paper)"
                stroke="var(--accent)"
                strokeWidth={2}
              />
            </g>
          )}
        </g>

        {/* axes */}
        <line
          x1={M.left}
          x2={W - M.right}
          y1={M.top + ih}
          y2={M.top + ih}
          stroke="var(--rule-strong)"
        />
        <line
          x1={M.left}
          x2={M.left}
          y1={M.top}
          y2={M.top + ih}
          stroke="var(--rule-strong)"
        />

        <text
          x={M.left + iw / 2}
          y={H - 2}
          textAnchor="middle"
          className="fill-[var(--ink-faint)] font-mono text-[9px]"
        >
          {xLabel}
        </text>
        <text
          x={-(M.top + ih / 2)}
          y={11}
          transform="rotate(-90)"
          textAnchor="middle"
          className="fill-[var(--ink-faint)] font-mono text-[9px]"
        >
          {yLabel}
        </text>
      </svg>

      <div className="mt-1 flex min-h-5 flex-wrap items-center gap-x-4 gap-y-1">
        {series
          .filter((s) => s.label)
          .map((s, i) => (
            <span
              key={i}
              className="flex items-center gap-1.5 font-mono text-[0.625rem] text-ink-faint"
            >
              <span
                className="h-0.5 w-3.5 rounded-full"
                style={{
                  background: s.color ?? "var(--accent)",
                  opacity: s.dashed ? 0.5 : 1,
                }}
              />
              {s.label}
            </span>
          ))}
        {hover && (
          <span className="ml-auto font-mono text-[0.625rem] text-ink">
            {xLabel.split(" ")[0]} {formatX(hover.x)} · {yLabel.split(" ")[0]}{" "}
            {formatY(hover.y)}
          </span>
        )}
      </div>
    </figure>
  );
}

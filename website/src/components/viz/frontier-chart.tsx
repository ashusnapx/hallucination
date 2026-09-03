"use client";

import { useId, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Cost against quality, with 95% intervals.
 *
 * A scatter rather than a bar chart, because the argument is a *shape*: quality
 * climbs steeply over the first 1.4 seconds and then goes flat. A bar chart of
 * AUROC would drop the cost axis entirely, which is the whole finding.
 *
 * Hand-rolled SVG rather than a charting library. Five points with bespoke
 * annotations and hand-placed labels is not what a generic chart library is
 * good at, and Recharts would cost ~50kB to draw this worse.
 *
 * Label placement is explicit per point. Two configurations sit at the same
 * cost (1.38s) and within 0.004 AUROC of each other, so an automatic
 * "label above the dot" rule collides every time.
 */
type Anchor = "start" | "middle" | "end";

const POINTS: {
  label: string;
  auroc: number;
  ci: readonly [number, number];
  cost: number;
  emphasis?: boolean;
  dx: number;
  dy: number;
  anchor: Anchor;
}[] = [
  {
    label: "surface only",
    auroc: 0.578,
    ci: [0.526, 0.63],
    cost: 0.0,
    dx: 12,
    dy: 4,
    anchor: "start",
  },
  {
    label: "token",
    auroc: 0.764,
    ci: [0.718, 0.806],
    cost: 1.38,
    emphasis: true,
    dx: 12,
    dy: -6,
    anchor: "start",
  },
  {
    label: "surface + token",
    auroc: 0.76,
    ci: [0.714, 0.803],
    cost: 1.38,
    dx: 12,
    dy: 14,
    anchor: "start",
  },
  {
    label: "sampling only",
    auroc: 0.739,
    ci: [0.691, 0.778],
    cost: 8.55,
    dx: -10,
    dy: 16,
    anchor: "end",
  },
  {
    label: "all three",
    auroc: 0.776,
    ci: [0.733, 0.813],
    cost: 9.93,
    emphasis: true,
    dx: -6,
    dy: -22,
    anchor: "end",
  },
];

export function FrontierChart({ className }: { className?: string }) {
  const clip = useId();
  const [active, setActive] = useState<number | null>(null);

  const W = 620;
  const H = 320;
  const M = { top: 26, right: 28, bottom: 46, left: 52 };
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;

  const xMax = 11;
  const yMin = 0.54;
  const yMax = 0.82;

  const x = (cost: number) => M.left + (cost / xMax) * iw;
  const y = (auroc: number) =>
    M.top + ih - ((auroc - yMin) / (yMax - yMin)) * ih;

  const pts = POINTS.map((p, i) => ({
    ...p,
    i,
    cx: x(p.cost),
    cy: y(p.auroc),
  }));
  const token = pts.find((p) => p.label === "token")!;
  const all = pts.find((p) => p.label === "all three")!;

  return (
    <figure className={cn("w-full", className)}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label="Detection quality against cost per query. Token signals reach 0.764 AUROC at 1.38 seconds; adding sampling reaches 0.776 at 9.93 seconds, a 7-fold cost increase for 0.012 AUROC."
      >
        <defs>
          <clipPath id={clip}>
            <rect x={M.left} y={M.top - 10} width={iw} height={ih + 10} />
          </clipPath>
        </defs>

        {[0.6, 0.7, 0.8].map((v) => (
          <g key={v}>
            <line
              x1={M.left}
              x2={W - M.right}
              y1={y(v)}
              y2={y(v)}
              stroke="var(--rule)"
              strokeDasharray="3 5"
            />
            <text
              x={M.left - 10}
              y={y(v)}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-[var(--ink-faint)] font-mono text-[10px]"
            >
              {v.toFixed(2)}
            </text>
          </g>
        ))}

        {/* axis floor */}
        <line
          x1={M.left}
          x2={W - M.right}
          y1={M.top + ih}
          y2={M.top + ih}
          stroke="var(--rule-strong)"
        />

        {[0, 2, 4, 6, 8, 10].map((v) => (
          <text
            key={v}
            x={x(v)}
            y={M.top + ih + 18}
            textAnchor="middle"
            className="fill-[var(--ink-faint)] font-mono text-[10px]"
          >
            {v}s
          </text>
        ))}

        {/* The comparison the section is arguing about */}
        <g clipPath={`url(#${clip})`}>
          <line
            x1={token.cx}
            x2={all.cx}
            y1={token.cy}
            y2={all.cy}
            stroke="var(--accent)"
            strokeDasharray="4 4"
            opacity={0.45}
          />
        </g>
        <text
          x={(token.cx + all.cx) / 2}
          y={token.cy - 22}
          textAnchor="middle"
          className="fill-[var(--ink-muted)] font-mono text-[10px]"
        >
          +0.012 AUROC · 7× the time
        </text>

        {pts.map((p) => {
          const isActive = active === p.i;
          return (
            <g
              key={p.label}
              onMouseEnter={() => setActive(p.i)}
              onMouseLeave={() => setActive(null)}
              className="cursor-default"
            >
              <line
                x1={p.cx}
                x2={p.cx}
                y1={y(p.ci[0])}
                y2={y(p.ci[1])}
                stroke={p.emphasis ? "var(--accent)" : "var(--ink-faint)"}
                strokeWidth={isActive ? 3 : 1.5}
                strokeLinecap="round"
                opacity={p.emphasis ? 0.45 : 0.28}
              />
              <circle
                cx={p.cx}
                cy={p.cy}
                r={isActive ? 7 : p.emphasis ? 5.5 : 4}
                fill={p.emphasis ? "var(--accent)" : "var(--paper)"}
                stroke={p.emphasis ? "var(--accent)" : "var(--ink-faint)"}
                strokeWidth={1.5}
                className="transition-all duration-150"
              />
              <text
                x={p.cx + p.dx}
                y={p.cy + p.dy}
                textAnchor={p.anchor}
                className={cn(
                  "font-mono text-[10px]",
                  p.emphasis ? "fill-[var(--ink)]" : "fill-[var(--ink-faint)]",
                )}
              >
                {p.label}
              </text>
              <text
                x={p.cx + p.dx}
                y={p.cy + p.dy + 12}
                textAnchor={p.anchor}
                className="fill-[var(--ink-faint)] font-mono text-[10px]"
              >
                {p.auroc.toFixed(3)}
              </text>
            </g>
          );
        })}

        <text
          x={M.left + iw / 2}
          y={H - 6}
          textAnchor="middle"
          className="fill-[var(--ink-faint)] font-mono text-[10px]"
        >
          seconds per query
        </text>
        <text
          x={-(M.top + ih / 2)}
          y={14}
          transform="rotate(-90)"
          textAnchor="middle"
          className="fill-[var(--ink-faint)] font-mono text-[10px]"
        >
          AUROC
        </text>
      </svg>

      <figcaption className="mt-1 text-[0.75rem] leading-relaxed text-ink-faint">
        Vertical bars are 95% bootstrap intervals. They overlap almost entirely
        between the cheap and the expensive configuration, which is the honest
        reading: on short-form QA with a 3B model, sampling is not buying much.
      </figcaption>
    </figure>
  );
}

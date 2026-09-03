"use client";

import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "motion/react";
import {
  AlertTriangle,
  CheckCircle2,
  MinusCircle,
  ShieldAlert,
} from "lucide-react";
import { DECISION_META, type Decision } from "@/lib/halluciwatch";
import { cn } from "@/lib/utils";

const ICONS: Record<Decision, typeof CheckCircle2> = {
  accept: CheckCircle2,
  review: AlertTriangle,
  reject: ShieldAlert,
  abstain: MinusCircle,
};

/**
 * The instrument face: a 240° arc reading 0–1 risk.
 *
 * An arc rather than a bar because this is the page's primary readout and it
 * should look like a gauge on equipment. The needle and the numeral animate
 * together so the number is never ahead of the mark it refers to.
 *
 * Colour alone never carries the verdict — an icon and the decision word ride
 * alongside it, which is what makes the risk ramp safe for colour-vision
 * deficiency.
 */
export function RiskDial({
  risk,
  decision,
  calibrated,
  size = 208,
}: {
  risk: number;
  decision: Decision;
  calibrated: boolean;
  size?: number;
}) {
  const meta = DECISION_META[decision];
  const Icon = ICONS[decision];
  const reduce = useReducedMotion();
  const [animated, setAnimated] = useState(0);
  const prev = useRef(0);

  // Derive rather than store: with reduced motion the dial simply reads the
  // real value, so no effect has to write state to catch up.
  const shown = reduce ? risk : animated;

  useEffect(() => {
    if (reduce) return;
    const controls = animate(prev.current, risk, {
      duration: 1.1,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: setAnimated,
    });
    prev.current = risk;
    return () => controls.stop();
  }, [risk, reduce]);

  const SWEEP = 240; // degrees of travel
  const START = 150; // 0 sits lower-left, 1 lower-right
  const stroke = 10;
  const r = (size - stroke * 2) / 2 - 6;
  const cx = size / 2;
  const cy = size / 2;

  const track = describeArc(cx, cy, r, START, START + SWEEP);
  const value = describeArc(cx, cy, r, START, START + SWEEP * clamp(shown));

  const angle = ((START + SWEEP * clamp(shown)) * Math.PI) / 180;
  const tickX = cx + Math.cos(angle) * (r + 9);
  const tickY = cy + Math.sin(angle) * (r + 9);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size * 0.78 }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="overflow-visible"
          role="img"
          aria-label={`Hallucination risk ${(risk * 100).toFixed(0)} percent, decision ${meta.label}`}
        >
          <path
            d={track}
            fill="none"
            stroke="var(--rule)"
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          <path
            d={value}
            fill="none"
            stroke={`var(--risk-${meta.token})`}
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          {/* The needle tick reads as a measurement mark rather than decoration. */}
          <circle
            cx={tickX}
            cy={tickY}
            r={3.5}
            fill={`var(--risk-${meta.token})`}
          />
        </svg>

        <div className="absolute inset-x-0 top-[38%] flex flex-col items-center">
          <div className="flex items-baseline font-mono text-ink">
            <span className="text-[2.75rem] leading-none font-medium tracking-tight">
              {(shown * 100).toFixed(0)}
            </span>
            <span className="ml-0.5 text-lg text-ink-faint">%</span>
          </div>
          <span className="eyebrow mt-1.5">risk</span>
        </div>
      </div>

      <div
        className={cn(
          "-mt-1 inline-flex items-center gap-1.5 rounded-pill border px-3 py-1.5 text-[0.8125rem] font-medium",
        )}
        style={{
          borderColor: `var(--risk-${meta.token})`,
          background: `var(--risk-${meta.token}-wash)`,
          color: `var(--risk-${meta.token})`,
        }}
      >
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {meta.label}
      </div>

      <p className="mt-2.5 max-w-[16rem] text-center text-[0.8125rem] leading-snug text-ink-muted">
        {meta.blurb}
      </p>

      {!calibrated && (
        <p className="mt-2 max-w-[16rem] rounded-md border border-rule bg-paper-sunken px-2.5 py-1.5 text-center text-[0.6875rem] leading-snug text-ink-muted">
          Heuristic score — no trained model is loaded, so this is not a
          calibrated probability.
        </p>
      )}
    </div>
  );
}

function clamp(v: number) {
  return Math.min(Math.max(v, 0), 1);
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startDeg: number,
  endDeg: number,
) {
  const start = polar(cx, cy, r, startDeg);
  const end = polar(cx, cy, r, endDeg);
  const large = endDeg - startDeg <= 180 ? 0 : 1;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`;
}

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

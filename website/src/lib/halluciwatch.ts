/**
 * The contract with the Python backend.
 *
 * These types mirror `RiskReport.to_dict()` in
 * `backend/src/halluciwatch/types.py` exactly. When that changes, change this.
 */

export type Decision = "accept" | "review" | "reject" | "abstain";

export type Tier = "surface" | "token" | "sampling" | "verify";

export interface ScoreResult {
  risk: number;
  decision: Decision;
  answer: string;
  question: string;
  model: string;
  tiers_used: Tier[];
  /** [feature name, value], ranked by the trained model's gain. */
  top_factors: [string, number][];
  /** [token text, 0-1 normalised uncertainty] for the heat-map. */
  token_risk: [string, number][];
  /** Sampled answers grouped by meaning; empty when the cascade didn't escalate. */
  clusters: string[][];
  latency_s: number;
  /** Time spent scoring, excluding the generation that had to happen anyway. */
  overhead_s: number;
  calibrated: boolean;
  notes: string[];
  features: Record<string, number>;
}

export interface FeatureSpec {
  name: string;
  tier: Tier;
  description: string;
  higher_is_riskier: boolean;
}

export interface HealthResult {
  status: string;
  calibrated: boolean;
  tiers: Tier[];
  ollama: {
    host: string;
    version: string;
    models: string[];
    generation_model: string;
    generation_model_available: boolean;
    embed_model: string;
    embed_model_available: boolean;
  };
}

export class ScoreError extends Error {
  constructor(
    message: string,
    readonly kind: "backend-down" | "timeout" | "bad-request" | "unknown",
  ) {
    super(message);
    this.name = "ScoreError";
  }
}

export async function score(
  question: string,
  opts: { signal?: AbortSignal; samples?: number; answer?: string } = {},
): Promise<ScoreResult> {
  let res: Response;
  try {
    res = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        ...(opts.samples !== undefined ? { samples: opts.samples } : {}),
        ...(opts.answer ? { answer: opts.answer } : {}),
      }),
      signal: opts.signal,
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") throw err;
    throw new ScoreError("Could not reach the scoring API.", "backend-down");
  }

  const data = await res.json().catch(() => null);

  if (!res.ok || !data || data.error) {
    const message = data?.error ?? `Request failed with HTTP ${res.status}.`;
    const kind =
      res.status === 503
        ? "backend-down"
        : res.status === 504
          ? "timeout"
          : "bad-request";
    throw new ScoreError(message, kind);
  }
  return data as ScoreResult;
}

/* ── Presentation helpers ─────────────────────────────────────────────────── */

export const DECISION_META: Record<
  Decision,
  { label: string; blurb: string; token: string }
> = {
  accept: {
    label: "Accept",
    blurb: "Signals are stable. Safe to show.",
    token: "safe",
  },
  review: {
    label: "Review",
    blurb: "Ambiguous. Worth a human check.",
    token: "caution",
  },
  reject: {
    label: "Reject",
    blurb: "Likely unsupported. Don't show this.",
    token: "danger",
  },
  abstain: {
    label: "Abstain",
    blurb: "The model declined. Nothing was claimed.",
    token: "neutral",
  },
};

export const TIER_META: Record<
  Tier,
  { label: string; cost: string; blurb: string }
> = {
  surface: {
    label: "Surface",
    cost: "free",
    blurb: "Refusal, hedging and entity density, read straight off the text.",
  },
  token: {
    label: "Token",
    cost: "+5%",
    blurb:
      "Entropy, margin and varentropy of the model's own next-token distribution.",
  },
  sampling: {
    label: "Sampling",
    cost: "K× gen",
    blurb: "Ask again several times, then cluster the answers by meaning.",
  },
  verify: {
    label: "Verify",
    cost: "+1 gen",
    blurb:
      "Ask the model to grade itself. Off by default — measured at chance below 3B.",
  },
};

/** Registry prefix → tier, so a feature name alone identifies its family. */
export function tierOfFeature(name: string): Tier {
  if (name.startsWith("tok.")) return "token";
  if (name.startsWith("cns.")) return "sampling";
  if (name.startsWith("vrf.")) return "verify";
  return "surface";
}

export function prettyFeature(name: string): string {
  return name.replace(/^[a-z]+\./, "").replace(/_/g, " ");
}

/** Format a measurement for display without lying about precision. */
export function formatValue(value: number): string {
  if (Number.isInteger(value)) return String(value);
  if (Math.abs(value) >= 100) return value.toFixed(0);
  if (Math.abs(value) >= 10) return value.toFixed(1);
  return value.toFixed(3);
}

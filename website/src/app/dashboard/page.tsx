import type { Metadata } from "next";
import { PageHeader } from "@/components/site/page-header";
import { NextPage } from "@/components/site/next-page";
import { Scorecard } from "@/components/dashboard/scorecard";
import {
  ConfusionPanel,
  FeaturePanel,
  ImportancePanel,
  Panel,
  PrPanel,
  ReliabilityPanel,
  RiskCoveragePanel,
  RocPanel,
  ScoreDistributionPanel,
  TierPanel,
} from "@/components/dashboard/panels";
import { FrontierChart } from "@/components/viz/frontier-chart";
import { HoldoutPanel } from "@/components/dashboard/holdout";
import { Findings } from "@/components/sections/findings";
import { PAPERS, PHASES } from "@/lib/proposal";
import data from "@/data/dashboard.json";

export const metadata: Metadata = {
  title: "Dashboard",
  description:
    "Every measurement from the HalluciWatch study: ROC, precision–recall, calibration, risk–coverage, per-tier ablation, and the project scored against its own Phase-1 targets.",
};

const HEADLINE = [
  {
    label: "AUROC",
    value: data.headline.auroc.toFixed(3),
    sub: `95% CI [${data.headline.auroc_ci[0]}, ${data.headline.auroc_ci[1]}]`,
  },
  {
    label: "AUPRC",
    value: data.headline.auprc.toFixed(3),
    sub: `base rate ${(data.headline.base_rate * 100).toFixed(1)}%`,
  },
  { label: "F1", value: data.headline.f1.toFixed(3), sub: "at threshold 0.5" },
  {
    label: "Precision",
    value: data.headline.precision.toFixed(3),
    sub: "of flagged answers",
  },
  {
    label: "Recall",
    value: data.headline.recall.toFixed(3),
    sub: "of hallucinations caught",
  },
  { label: "ECE", value: data.headline.ece.toFixed(3), sub: "cross-fitted" },
  {
    label: "Brier",
    value: data.headline.brier.toFixed(3),
    sub: "squared error",
  },
  {
    label: "Accuracy",
    value: data.headline.accuracy.toFixed(3),
    sub: "at threshold 0.5",
  },
];

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Dashboard"
        title={
          <>
            Every number, and <em>where it came from</em>
          </>
        }
        lede="The full measurement set for the Phase-1 study, exported straight from the trained model and the corpus. Nothing on this page is hand-entered."
        meta={[
          { label: "Model", value: data.headline.model },
          { label: "Rows", value: `${data.headline.n}` },
          { label: "Features", value: `${data.headline.n_features}` },
          { label: "Validation", value: `${5}-fold, grouped` },
          { label: "Exported", value: data.generated_at },
        ]}
      />

      <div className="mx-auto max-w-(--container-wide) space-y-14 px-(--spacing-gutter) py-12 sm:py-16">
        {/* ── Scorecard ─────────────────────────────────────────────────── */}
        <section>
          <h2 className="font-display text-heading">
            Scored against the Phase-1 proposal
          </h2>
          <p className="mt-2 max-w-2xl text-[0.875rem] leading-relaxed text-ink-muted">
            Eleven deliverables were promised in the synopsis and slide deck.
            Here is each one against what was actually built, including the two
            targets that were missed.
          </p>
          <div className="mt-6">
            <Scorecard />
          </div>
        </section>

        {/* ── Headline metrics ──────────────────────────────────────────── */}
        <section>
          <h2 className="font-display text-heading">Classifier performance</h2>
          <p className="mt-2 max-w-2xl text-[0.875rem] leading-relaxed text-ink-muted">
            Cross-validated with folds grouped by question, so no question
            appears in both train and test. Ranking metrics come from raw
            out-of-fold scores; calibration metrics from cross-fitted isotonic
            probabilities.
          </p>
          <dl className="mt-6 grid gap-px overflow-hidden rounded-card border border-rule bg-rule sm:grid-cols-2 lg:grid-cols-4">
            {HEADLINE.map((m) => (
              <div key={m.label} className="bg-paper px-4 py-5">
                <dt className="eyebrow">{m.label}</dt>
                <dd className="mt-1.5 font-mono text-[1.625rem] leading-none text-ink">
                  {m.value}
                </dd>
                <dd className="mt-1.5 font-mono text-[0.625rem] text-ink-faint">
                  {m.sub}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        {/* ── Curves ────────────────────────────────────────────────────── */}
        <section>
          <h2 className="font-display text-heading">Diagnostic curves</h2>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <RocPanel />
            <PrPanel />
            <ReliabilityPanel />
            <RiskCoveragePanel />
          </div>
        </section>

        {/* ── Errors ────────────────────────────────────────────────────── */}
        <section>
          <h2 className="font-display text-heading">
            Where it gets things wrong
          </h2>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <ScoreDistributionPanel />
            <ConfusionPanel />
          </div>
        </section>

        {/* ── Signals ───────────────────────────────────────────────────── */}
        <section>
          <h2 className="font-display text-heading">
            The fingerprint, broken down
          </h2>
          <p className="mt-2 max-w-2xl text-[0.875rem] leading-relaxed text-ink-muted">
            {data.headline.n_features} features across three tiers. The two
            rankings below disagree, which is itself the finding: the model
            leans on the sampling features, while the strongest feature measured
            alone is a token-entropy statistic.
          </p>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <FeaturePanel />
            <ImportancePanel />
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <TierPanel />
            <CorpusPanel />
          </div>

          <div className="mt-4 rounded-card border border-rule bg-paper-raised p-5 shadow-card">
            <h3 className="eyebrow">Cost against quality</h3>
            <p className="mt-1.5 max-w-2xl text-[0.75rem] leading-relaxed text-ink-faint">
              The measurement the architecture rests on. Quality climbs steeply
              over the first 1.4 seconds and then goes flat.
            </p>
            <div className="mt-4 max-w-3xl">
              <FrontierChart />
            </div>
          </div>
        </section>

        {/* ── Generalisation ────────────────────────────────────────────── */}
        <section>
          <h2 className="font-display text-heading">
            Does it transfer to benchmarks it never saw?
          </h2>
          <p className="mt-2 max-w-2xl text-[0.875rem] leading-relaxed text-ink-muted">
            The synopsis named TruthfulQA and SimpleQA. Both are held out
            entirely from training, and the result is more interesting than a
            clean number.
          </p>
          <div className="mt-6">
            <HoldoutPanel />
          </div>
        </section>

        {/* ── Negative results ──────────────────────────────────────────── */}
        <section>
          <h2 className="font-display text-heading">What didn&rsquo;t work</h2>
          <p className="mt-2 max-w-2xl text-[0.875rem] leading-relaxed text-ink-muted">
            Four measurements that make the project look worse. They are here
            because a detector you cannot audit is worth nothing, and because
            each one changed what the code does.
          </p>
          <Findings bare />
        </section>

        {/* ── Pipeline ──────────────────────────────────────────────────── */}
        <section>
          <h2 className="font-display text-heading">
            The four-phase pipeline, as proposed and as built
          </h2>
          <ol className="mt-6 grid gap-px overflow-hidden rounded-card border border-rule bg-rule sm:grid-cols-2">
            {PHASES.map((p) => (
              <li key={p.n} className="bg-paper p-5 sm:p-6">
                <span className="font-mono text-[0.6875rem] text-ink-faint">
                  {p.n}
                </span>
                <h3 className="mt-1.5 font-display text-[1.125rem]">
                  {p.title}
                </h3>
                <dl className="mt-3 space-y-3">
                  <div>
                    <dt className="font-mono text-[0.5625rem] uppercase tracking-wide text-ink-faint">
                      proposed
                    </dt>
                    <dd className="mt-1 text-[0.8125rem] leading-relaxed text-ink-faint">
                      {p.proposed}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-mono text-[0.5625rem] uppercase tracking-wide text-ink-faint">
                      built
                    </dt>
                    <dd className="mt-1 text-[0.8125rem] leading-relaxed text-ink-muted">
                      {p.built}
                    </dd>
                  </div>
                </dl>
              </li>
            ))}
          </ol>
        </section>

        {/* ── Literature ────────────────────────────────────────────────── */}
        <section>
          <h2 className="font-display text-heading">
            Literature review — 15 papers
          </h2>
          <p className="mt-2 max-w-2xl text-[0.875rem] leading-relaxed text-ink-muted">
            The Phase-1 survey. Paper 12 (LLM-Check) is the direct theoretical
            basis for reading internal signals; paper 6 is the reason a
            fingerprint should not be assumed adversarially robust.
          </p>
          <div className="mt-6 overflow-x-auto rounded-card border border-rule">
            <table className="w-full min-w-[46rem] text-left text-[0.8125rem]">
              <thead>
                <tr className="border-b border-rule bg-paper-sunken">
                  <th className="px-4 py-2.5 font-medium text-ink-muted">#</th>
                  <th className="px-4 py-2.5 font-medium text-ink-muted">
                    Topic
                  </th>
                  <th className="px-4 py-2.5 font-medium text-ink-muted">
                    Method
                  </th>
                  <th className="px-4 py-2.5 font-medium text-ink-muted">
                    Key finding
                  </th>
                  <th className="px-4 py-2.5 font-medium text-ink-muted">
                    Group
                  </th>
                </tr>
              </thead>
              <tbody>
                {PAPERS.map((p) => (
                  <tr key={p.n} className="border-b border-rule last:border-0">
                    <td className="px-4 py-2.5 font-mono text-ink-faint">
                      {p.n}
                    </td>
                    <td className="px-4 py-2.5 text-ink">{p.topic}</td>
                    <td className="px-4 py-2.5 text-ink-muted">{p.method}</td>
                    <td className="px-4 py-2.5 text-ink-muted">{p.finding}</td>
                    <td className="px-4 py-2.5">
                      <span className="rounded-pill border border-rule px-2 py-0.5 font-mono text-[0.625rem] text-ink-faint">
                        {p.group}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <NextPage
        href="/demo"
        eyebrow="Next"
        title="See it score a live answer"
        blurb="Run the detector against a real local model and watch the cascade decide."
      />
    </>
  );
}

/* Corpus composition and the latency budget, kept beside the tier table. */
function CorpusPanel() {
  const l = data.latency;
  return (
    <Panel
      title="Corpus & latency"
      hint="What the study ran on, and how the overhead compares to the 50 ms the proposal targeted."
    >
      <dl className="space-y-2 text-[0.8125rem]">
        {[
          ["rows generated", `${data.corpus.rows_generated}`],
          ["used for training", `${data.corpus.rows_used}`],
          ["refusals excluded", `${data.corpus.refusals_excluded}`],
          [
            "sources",
            Object.entries(data.corpus.sources)
              .map(([k, v]) => `${k} (${v})`)
              .join(", "),
          ],
          [
            "grading",
            Object.entries(data.corpus.graders)
              .map(([k, v]) => `${k} (${v})`)
              .join(", "),
          ],
          ["median answer", `${data.corpus.median_tokens} tokens`],
        ].map(([k, v]) => (
          <div
            key={k}
            className="flex justify-between gap-4 border-b border-rule pb-2 last:border-0"
          >
            <dt className="shrink-0 text-ink-faint">{k}</dt>
            <dd className="text-right font-mono text-[0.75rem] text-ink">
              {v}
            </dd>
          </div>
        ))}
      </dl>

      <div className="mt-4 space-y-2 border-t border-rule pt-4">
        <LatencyBar
          label="tier 1 (token)"
          seconds={l.tier1_overhead_s}
          budget={l.target_ms / 1000}
        />
        <LatencyBar
          label="tier 2 (sampling)"
          seconds={l.tier2_overhead_s}
          budget={l.target_ms / 1000}
        />
      </div>
    </Panel>
  );
}

function LatencyBar({
  label,
  seconds,
  budget,
}: {
  label: string;
  seconds: number;
  budget: number;
}) {
  const within = seconds <= budget;
  // Log-ish scale: tier 2 is 400x the budget, so a linear bar would be useless.
  const pct = Math.min(
    100,
    (Math.log10(seconds * 1000 + 1) / Math.log10(10000)) * 100,
  );
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[0.75rem] text-ink-muted">{label}</span>
        <span
          className="font-mono text-[0.75rem]"
          style={{ color: `var(--risk-${within ? "safe" : "caution"})` }}
        >
          {seconds < 1
            ? `${(seconds * 1000).toFixed(0)} ms`
            : `${seconds.toFixed(2)} s`}
          {within ? " ✓" : " over budget"}
        </span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-paper-sunken">
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            background: `var(--risk-${within ? "safe" : "caution"})`,
          }}
        />
      </div>
    </div>
  );
}

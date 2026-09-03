import { TIER_META } from "@/lib/halluciwatch";
import { Reveal } from "@/components/ui/reveal";

const STEPS = [
  {
    n: "01",
    title: "The model answers, as it would anyway",
    body: "HalluciWatch wraps the generation you already wanted. Ollama returns per-token logprobs alongside the text, so the signal arrives with the answer rather than after it.",
    detail: "logprobs: true, top_logprobs: 20",
  },
  {
    n: "02",
    title: "Read the shape of its uncertainty",
    body: "At every token the model had a distribution over what to say next. Entropy, varentropy, the margin between the top two candidates, and where uncertainty falls on content words rather than grammar.",
    detail: "19 features, +5% wall-time",
  },
  {
    n: "03",
    title: "Escalate only when that is ambiguous",
    body: "If the cheap score lands in the uncertainty band, ask the model the same question several more times and cluster the answers by meaning. Disagreement across samples is semantic entropy.",
    detail: "K extra generations, only when needed",
  },
  {
    n: "04",
    title: "Return a calibrated probability, not a vibe",
    body: "Gradient boosting over the fingerprint, isotonic-calibrated so 0.30 means roughly three in ten. Accept and reject thresholds are fitted on held-out data to bound the error rate among answers you auto-accept.",
    detail: "ECE 0.048",
  },
];

export function HowItWorks() {
  return (
    <section className="border-t border-rule py-(--spacing-section)">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        <Reveal className="max-w-2xl">
          <span className="eyebrow">The solution</span>
          <h2 className="title mt-3">
            Read the model&rsquo;s <em>own uncertainty</em>
          </h2>
          <p className="mt-4 text-lede text-ink-muted">
            Four steps, escalating only when the cheap ones are ambiguous. Each
            tier is measured, and each one earns its place or gets switched off.
          </p>
        </Reveal>
        <ol className="mt-12 grid gap-px overflow-hidden rounded-card border border-rule bg-rule sm:grid-cols-2">
          {STEPS.map((s) => (
            <li key={s.n} className="bg-paper p-6 sm:p-7">
              <span className="font-mono text-[0.6875rem] text-ink-faint">
                {s.n}
              </span>
              <h3 className="mt-2.5 font-display text-heading">{s.title}</h3>
              <p className="mt-2.5 text-[0.875rem] leading-relaxed text-ink-muted">
                {s.body}
              </p>
              <p className="mt-3.5 font-mono text-[0.6875rem] text-ink-faint">
                {s.detail}
              </p>
            </li>
          ))}
        </ol>

        {/* The cost ladder, stated plainly. */}
        <div className="mt-10 overflow-hidden rounded-card border border-rule">
          <table className="w-full text-left text-[0.875rem]">
            <caption className="sr-only">
              Signal tiers and their measured cost
            </caption>
            <thead>
              <tr className="border-b border-rule bg-paper-sunken">
                <th
                  scope="col"
                  className="px-5 py-2.5 font-medium text-ink-muted"
                >
                  Tier
                </th>
                <th
                  scope="col"
                  className="px-5 py-2.5 font-medium text-ink-muted"
                >
                  What it reads
                </th>
                <th
                  scope="col"
                  className="px-5 py-2.5 text-right font-medium text-ink-muted"
                >
                  Cost
                </th>
              </tr>
            </thead>
            <tbody>
              {(["surface", "token", "sampling", "verify"] as const).map(
                (tier) => {
                  const meta = TIER_META[tier];
                  const off = tier === "verify";
                  return (
                    <tr
                      key={tier}
                      className="border-b border-rule last:border-0"
                    >
                      <th
                        scope="row"
                        className="px-5 py-3 font-medium text-ink"
                      >
                        {meta.label}
                        {off && (
                          <span className="ml-2 rounded-pill border border-rule px-1.5 py-0.5 font-mono text-[0.625rem] font-normal text-ink-faint">
                            off by default
                          </span>
                        )}
                      </th>
                      <td className="px-5 py-3 text-ink-muted">{meta.blurb}</td>
                      <td className="whitespace-nowrap px-5 py-3 text-right font-mono text-ink">
                        {meta.cost}
                      </td>
                    </tr>
                  );
                },
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

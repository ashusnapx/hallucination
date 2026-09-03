import { Reveal } from "@/components/ui/reveal";

/**
 * The problem statement, as submitted in the Phase-1 deck.
 *
 * Both figures are quoted from the proposal's own sources rather than restated
 * as this project's findings — they motivate the work, they are not results of
 * it, and the distinction matters on a page that otherwise only shows measured
 * numbers.
 */
const STATS = [
  {
    value: "30–40%",
    label: "of adversarial questions answered falsely",
    source: "TruthfulQA benchmark",
  },
  {
    value: "27%+",
    label: "of medical queries hallucinated by GPT-4",
    source: "clinical benchmark studies",
  },
];

const LIMITS = [
  {
    title: "They work after the fact",
    body: "The response is already rendered by the time a checker sees it. At that point the only options are a retraction or a warning label.",
  },
  {
    title: "They need something external",
    body: "A retrieval index, a fact-checking API, or a second and larger model to act as judge. Each one is a dependency, a bill and a privacy boundary.",
  },
  {
    title: "They cost real latency",
    body: "A judge call doubles time-to-answer at best. Guardrails that make a product feel slow get switched off.",
  },
];

export function Problem() {
  return (
    <section className="border-t border-rule py-(--spacing-section)">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        <Reveal className="max-w-2xl">
          <span className="eyebrow">The problem</span>
          <h2 className="title mt-3">
            Fluent, confident, and <em>wrong</em>
          </h2>
          <p className="mt-4 text-lede text-ink-muted">
            A language model uses the same tone whether it is stating a verified
            fact or inventing one. There is no internal truth check — it
            predicts the next likely word, and a plausible falsehood is often
            more likely than an admission of ignorance.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)] lg:gap-8">
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            {STATS.map((s) => (
              <div
                key={s.value}
                className="rounded-card border border-rule bg-paper-raised p-6"
              >
                <dt className="font-display text-[2.5rem] leading-none text-risk-danger">
                  {s.value}
                </dt>
                <dd className="mt-3 text-[0.875rem] leading-relaxed text-ink">
                  {s.label}
                </dd>
                <dd className="mt-1.5 font-mono text-[0.625rem] text-ink-faint">
                  {s.source}
                </dd>
              </div>
            ))}
          </dl>

          <div className="rounded-card border border-rule bg-paper-sunken p-6 sm:p-8">
            <h3 className="font-display text-heading">
              Why existing tools don&rsquo;t close it
            </h3>
            <dl className="mt-5 space-y-5">
              {LIMITS.map((l) => (
                <div
                  key={l.title}
                  className="border-t border-rule pt-4 first:border-0 first:pt-0"
                >
                  <dt className="text-[0.875rem] font-medium text-ink">
                    {l.title}
                  </dt>
                  <dd className="mt-1.5 text-[0.875rem] leading-relaxed text-ink-muted">
                    {l.body}
                  </dd>
                </div>
              ))}
            </dl>

            <p className="mt-7 border-t border-rule pt-5 text-[0.9375rem] leading-relaxed text-ink">
              The signal that a model is about to make something up is present{" "}
              <em>while it writes</em> — in the probability distribution it
              computes at every token. Reading it there costs one forward pass
              you were already paying for.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

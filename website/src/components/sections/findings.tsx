import { GITHUB_URL } from "@/lib/site";

/**
 * The negative results.
 *
 * This section is the product's actual differentiator, so it is given the same
 * weight as the benchmark section rather than being buried in a limitations
 * footnote. A measurement tool that hides its own unflattering numbers is not
 * one you should trust with yours.
 */
const FINDINGS = [
  {
    verdict: "One feature beats the whole model",
    numbers: "0.823 vs 0.818",
    body: (
      <>
        <code className="font-mono text-ink">tok.p90_entropy</code> alone still
        edges out all 36 features combined. Catching this the first time — when
        the gap was 0.789 vs 0.776 — is what prompted shrinking the model from
        depth-4 trees to depth-1 stumps, which recovered +0.017 AUROC. The gap
        is now nearly closed, but it has not reversed: most of the value here is
        one well-chosen uncertainty statistic.
      </>
    ),
  },
  {
    verdict: "Asking the model to check itself does nothing",
    numbers: "AUROC 0.500",
    body: (
      <>
        P(True) self-verification measured at exactly chance on a 1B model —
        0.527 mean on correct answers, 0.530 on wrong ones. Adding it{" "}
        <em>dropped</em> the combined model from 0.872 to 0.841, because an
        uninformative feature is not free. That tier ships off by default.
      </>
    ),
  },
  {
    verdict: "Surface features actively hurt",
    numbers: "0.8104 → 0.8095",
    body: (
      <>
        Hedging, length and entity density looked promising and are close to
        free, but token signals alone still edge out token-plus-surface. They
        stay in the registry so the ablation can keep re-testing them on your
        data, not because they earned their place on ours.
      </>
    ),
  },
  {
    verdict: "The expensive tier barely earns its cost",
    numbers: "7× time, +0.008",
    body: (
      <>
        Semantic entropy is the strongest idea in the literature and it is the
        reason the sampling tier exists. On short-form QA with a 3B model it
        moved AUROC from 0.810 to 0.818 for seven times the latency, with
        confidence intervals that overlap almost entirely. Hence a cascade
        rather than always paying.
      </>
    ),
  },
];

export function Findings({ bare = false }: { bare?: boolean } = {}) {
  return (
    <section className={bare ? "" : "pt-12 pb-(--spacing-section) sm:pt-16"}>
      <div
        className={
          bare ? "" : "mx-auto max-w-(--container-wide) px-(--spacing-gutter)"
        }
      >
        <div className="grid gap-px overflow-hidden rounded-card border border-rule bg-rule md:grid-cols-2">
          {FINDINGS.map((f) => (
            <article key={f.verdict} className="bg-paper p-6 sm:p-7">
              <div className="flex items-baseline justify-between gap-4">
                <h2 className="font-display text-heading text-balance">
                  {f.verdict}
                </h2>
                <span className="shrink-0 font-mono text-[0.75rem] text-risk-danger">
                  {f.numbers}
                </span>
              </div>
              <p className="mt-3 text-[0.875rem] leading-relaxed text-ink-muted">
                {f.body}
              </p>
            </article>
          ))}
        </div>

        <div className="mt-10 grid gap-6 rounded-card border border-rule bg-paper-sunken p-6 sm:p-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-12">
          <div>
            <h2 className="font-display text-heading">On novelty</h2>
            <p className="mt-3 text-[0.875rem] leading-relaxed text-ink-muted">
              This project’s original proposal claimed no existing system used a
              model’s internal signals to predict hallucination in real time.
              That claim is false.{" "}
              <a
                href="https://arxiv.org/abs/2403.06448"
                target="_blank"
                rel="noreferrer noopener"
                className="underline underline-offset-2 hover:text-ink"
              >
                MIND (2024)
              </a>{" "}
              is literally titled{" "}
              <em>
                Unsupervised Real-Time Hallucination Detection based on the
                Internal States of Large Language Models
              </em>
              , and{" "}
              <a
                href="https://github.com/IINemo/lm-polygraph"
                target="_blank"
                rel="noreferrer noopener"
                className="underline underline-offset-2 hover:text-ink"
              >
                LM-Polygraph
              </a>{" "}
              ships dozens of these estimators.
            </p>
            <p className="mt-3 text-[0.875rem] leading-relaxed text-ink-muted">
              The gap is not scientific priority. It is that none of this is
              packaged as a cost-aware, calibrated runtime guardrail with
              abstention that runs on a laptop.
            </p>
          </div>

          <div>
            <h2 className="font-display text-heading">
              On the original targets
            </h2>
            <p className="mt-3 text-[0.875rem] leading-relaxed text-ink-muted">
              The proposal targeted F1 &gt; 0.85 and AUROC &gt; 0.90. Measured
              here:{" "}
              <span className="font-mono text-ink">F1 0.757, AUROC 0.818</span>{" "}
              — short of both, after two rounds of legitimate improvement.
            </p>
            <p className="mt-3 text-[0.875rem] leading-relaxed text-ink-muted">
              Those literature numbers come from larger models with true
              white-box access, longer generations where semantic entropy has
              more to work with, and easier label distributions. A 3B quantised
              model answering short-form trivia through a gray-box API is a
              harder setting. Reporting 0.818 with its interval is more useful
              than tuning until a target is hit.
            </p>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-4 inline-block font-mono text-[0.75rem] text-ink-muted underline underline-offset-4 hover:text-ink"
            >
              make build &amp;&amp; make train &amp;&amp; make ablate
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

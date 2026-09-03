import { Reveal } from "@/components/ui/reveal";
import { CheckCircle2, HelpCircle } from "lucide-react";

/**
 * The golden test set, explained without assuming the reader knows what
 * inter-rater reliability is.
 *
 * This section exists because the label-quality problem is genuinely the most
 * interesting thing the project found, and it is invisible unless someone
 * spells out *why* a wrong label is worse than a wrong prediction.
 */

/** Real rows the string matcher got wrong, from the corpus. */
const MISLABELS = [
  {
    q: "Where would you find myoglobin?",
    said: "Muscle cells",
    gold: "Muscle tissue",
  },
  {
    q: "Warren Beatty's first movie?",
    said: "Splendour",
    gold: "Splendor in the Grass",
  },
  {
    q: "Eddie Murphy's first movie?",
    said: "48 Hrs.",
    gold: "48 Hours",
  },
];

const STATS = [
  { value: "510", label: "answers checked" },
  { value: "448", label: "both graders agreed" },
  { value: "62", label: "they disagreed" },
  { value: "0.76", label: "agreement score (κ)" },
];

export function Golden() {
  return (
    <section className="border-t border-rule py-(--spacing-section)">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        <Reveal className="max-w-2xl">
          <span className="eyebrow">Checking our own homework</span>
          <h2 className="title mt-3">
            How do you know the <em>answer key</em> is right?
          </h2>
          <p className="mt-4 text-lede text-ink-muted">
            To measure whether our tool works, we first need to know which
            answers were actually wrong. That answer key turned out to have
            mistakes in it — and fixing them mattered more than any change we
            made to the tool itself.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:gap-8">
          {/* The problem, shown rather than described */}
          <div className="rounded-card border border-rule bg-paper-raised p-6 sm:p-8">
            <h3 className="font-display text-heading">The problem</h3>
            <p className="mt-3 text-[0.9375rem] leading-relaxed text-ink-muted">
              We started by marking an answer &ldquo;wrong&rdquo; if it did not
              match the official answer word-for-word. That is fast, but it
              punishes answers that are perfectly correct and just worded
              differently:
            </p>

            <ul className="mt-5 space-y-2">
              {MISLABELS.map((m) => (
                <li
                  key={m.q}
                  className="rounded-card border border-rule bg-paper-sunken p-4"
                >
                  <p className="font-mono text-[0.75rem] text-ink-faint">
                    {m.q}
                  </p>
                  <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1 font-mono text-[0.8125rem]">
                    <span className="text-ink">
                      AI said &ldquo;{m.said}&rdquo;
                    </span>
                    <span className="text-ink-faint">
                      · key said &ldquo;{m.gold}&rdquo;
                    </span>
                  </div>
                  <p className="mt-2 font-mono text-[0.6875rem] text-risk-danger">
                    marked WRONG — but it is right
                  </p>
                </li>
              ))}
            </ul>

            <p className="mt-5 border-t border-rule pt-4 text-[0.875rem] leading-relaxed text-ink-muted">
              This matters more than it sounds. If the answer key is wrong, our
              tool gets punished for being right — and no amount of improving
              the tool can fix that.
            </p>
          </div>

          {/* The fix */}
          <div className="min-w-0">
            <div className="rounded-card border border-rule bg-paper-raised p-6 sm:p-8">
              <h3 className="font-display text-heading">The fix</h3>
              <p className="mt-3 text-[0.9375rem] leading-relaxed text-ink-muted">
                We graded every answer <b>twice</b>, using two methods that
                cannot copy each other:
              </p>

              <ol className="mt-4 space-y-3">
                {[
                  "The word-matching check, as before.",
                  "A second, larger AI acting as an examiner — one that did not write the answer it is grading.",
                ].map((t, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="mt-0.5 font-mono text-[0.6875rem] text-ink-faint">
                      {i + 1}
                    </span>
                    <span className="text-[0.875rem] leading-relaxed text-ink-muted">
                      {t}
                    </span>
                  </li>
                ))}
              </ol>

              <dl className="mt-5 space-y-3 border-t border-rule pt-4">
                <div className="flex gap-3">
                  <CheckCircle2
                    className="mt-0.5 h-4 w-4 shrink-0 text-risk-safe"
                    aria-hidden
                  />
                  <div>
                    <dt className="text-[0.875rem] font-medium text-ink">
                      When both agreed
                    </dt>
                    <dd className="mt-0.5 text-[0.875rem] leading-relaxed text-ink-muted">
                      We trust the label. Two independent methods reaching the
                      same verdict is strong evidence.
                    </dd>
                  </div>
                </div>
                <div className="flex gap-3">
                  <HelpCircle
                    className="mt-0.5 h-4 w-4 shrink-0 text-risk-caution"
                    aria-hidden
                  />
                  <div>
                    <dt className="text-[0.875rem] font-medium text-ink">
                      When they disagreed
                    </dt>
                    <dd className="mt-0.5 text-[0.875rem] leading-relaxed text-ink-muted">
                      We set it aside for a human to settle, rather than quietly
                      picking whichever grader we happened to prefer.
                    </dd>
                  </div>
                </div>
              </dl>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-card border border-rule bg-rule">
              {STATS.map((s) => (
                <div key={s.label} className="bg-paper px-4 py-4">
                  <dt className="font-mono text-[1.375rem] leading-none text-ink">
                    {s.value}
                  </dt>
                  <dd className="mt-1.5 text-[0.75rem] leading-snug text-ink-muted">
                    {s.label}
                  </dd>
                </div>
              ))}
            </dl>

            <p className="mt-3 text-[0.75rem] leading-relaxed text-ink-faint">
              κ (kappa) is a standard score for how much two graders agree,
              after subtracting the agreement you would expect from pure luck.
              0.76 counts as &ldquo;substantial&rdquo;.
            </p>
          </div>
        </div>

        {/* The payoff */}
        <Reveal>
          <div className="mt-4 rounded-card border border-rule bg-paper-sunken p-6 sm:p-8">
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center lg:gap-10">
              <div>
                <h3 className="font-display text-heading">
                  What cleaning the answer key was worth
                </h3>
                <p className="mt-2.5 max-w-2xl text-[0.875rem] leading-relaxed text-ink-muted">
                  Re-training on only the 448 answers both graders agreed on
                  improved our score more than any change we made to the tool.
                  One caveat worth stating: the second grader is an AI too, so
                  it is a cross-check, not a human ground truth — which is
                  exactly why the 62 disagreements are kept aside instead of
                  being resolved automatically.
                </p>
              </div>

              <div className="flex shrink-0 items-center gap-4">
                {[
                  { v: "0.776", l: "before", dim: true },
                  { v: "0.793", l: "after model fix", dim: true },
                  { v: "0.818", l: "after clean key", dim: false },
                ].map((x, i) => (
                  <div key={x.l} className="flex items-center gap-4">
                    {i > 0 && (
                      <span className="text-ink-faint" aria-hidden>
                        →
                      </span>
                    )}
                    <div>
                      <div
                        className={
                          x.dim
                            ? "font-mono text-[1.25rem] text-ink-faint"
                            : "font-mono text-[1.75rem] text-risk-safe"
                        }
                      >
                        {x.v}
                      </div>
                      <div className="mt-1 font-mono text-[0.625rem] text-ink-faint">
                        {x.l}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

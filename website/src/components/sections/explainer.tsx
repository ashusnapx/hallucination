import { Reveal } from "@/components/ui/reveal";
import { cn } from "@/lib/utils";

/**
 * The plain-language story, for a reader who knows nothing about LLMs.
 *
 * Written to assume no background at all: no jargon appears without being
 * defined in the same breath, every abstraction is anchored to the same
 * concrete example (the Fiddler question), and the numbers are explained in
 * terms of what they mean rather than what they are called.
 */

const STEPS = [
  {
    n: "1",
    q: "What is an AI “hallucination”?",
    a: (
      <>
        It is when an AI confidently tells you something that is simply not
        true. Not a typo, not a “sorry, I don’t know” — a clean, fluent,
        completely made-up answer, delivered in exactly the same tone it uses
        for facts.
      </>
    ),
    example: {
      label: "A real example from this project",
      q: "Where was the Fiddler in the musical’s title?",
      a: "On a violin.",
      why: "The musical is Fiddler on the Roof. The answer sounds reasonable — a fiddler is on a violin — but it is wrong, and nothing in the wording warns you.",
    },
  },
  {
    n: "2",
    q: "Why is that hard to catch?",
    a: (
      <>
        Because the AI has no idea it is wrong. It is not looking anything up.
        It is predicting the next likely word, over and over. A believable
        falsehood is often a more likely sequence of words than an honest “I
        don’t know” — so that is what comes out, in the same confident voice.
      </>
    ),
  },
  {
    n: "3",
    q: "So what can you actually measure?",
    a: (
      <>
        Here is the useful part. Before the AI writes each word, it internally
        ranks every word it might say next, with a score for each. When it knows
        something, one word wins by a mile. When it is making something up, lots
        of words score about the same — it is effectively guessing between them.
        <br />
        <br />
        That spread is the tell. We read it.
      </>
    ),
    compare: [
      {
        q: "What is the capital of France?",
        best: "Paris",
        spread: "Paris wins overwhelmingly",
        verdict: "sure",
        tone: "safe" as const,
      },
      {
        q: "Where was the Fiddler…?",
        best: "On",
        spread: "several words nearly tie",
        verdict: "guessing",
        tone: "danger" as const,
      },
    ],
  },
  {
    n: "4",
    q: "And if the spread doesn’t settle it?",
    a: (
      <>
        Then we ask the same question a few more times. An AI that knows the
        answer gives you the same one every time. An AI that is inventing gives
        you a different story each time. We group the answers by meaning and
        count how many distinct stories came back.
        <br />
        <br />
        This is slower, so we only do it when the first check is unclear.
      </>
    ),
  },
  {
    n: "5",
    q: "What do you get at the end?",
    a: (
      <>
        A single number between 0 and 1 — the chance this answer is unsupported
        — plus a plain verdict: <b>accept</b>, <b>review</b>, <b>reject</b>, or{" "}
        <b>abstain</b> (the AI declined to answer, which is honest rather than
        wrong).
        <br />
        <br />
        The number is <i>calibrated</i>, which means it is tuned so that it can
        be taken literally: out of the answers scored 0.30, about 30 in 100
        really do turn out to be wrong.
      </>
    ),
  },
];

export function Explainer() {
  return (
    <section className="border-t border-rule py-(--spacing-section)">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        <Reveal className="max-w-2xl">
          <span className="eyebrow">Start here</span>
          <h2 className="title mt-3">
            The whole idea, in <em>five questions</em>
          </h2>
          <p className="mt-4 text-lede text-ink-muted">
            No background needed. If you have ever used ChatGPT, you already
            know enough to follow all of this.
          </p>
        </Reveal>

        <ol className="mt-12 space-y-px overflow-hidden rounded-card border border-rule bg-rule">
          {STEPS.map((s) => (
            <li key={s.n} className="bg-paper p-6 sm:p-8">
              <div
                className={cn(
                  "grid gap-6 lg:gap-10",
                  (s.example || s.compare) &&
                    "lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]",
                )}
              >
                <div className="min-w-0">
                  <div className="flex items-baseline gap-3">
                    <span className="font-mono text-[0.6875rem] text-ink-faint">
                      {s.n}
                    </span>
                    <h3 className="font-display text-heading text-balance">
                      {s.q}
                    </h3>
                  </div>
                  <p className="mt-3 max-w-2xl text-[0.9375rem] leading-relaxed text-ink-muted">
                    {s.a}
                  </p>
                </div>

                <div
                  className={cn(
                    "min-w-0",
                    !s.example && !s.compare && "hidden",
                  )}
                >
                  {s.example && (
                    <div className="rounded-card border border-rule bg-paper-sunken p-5">
                      <span className="eyebrow">{s.example.label}</span>
                      <dl className="mt-3 space-y-2 font-mono text-[0.8125rem]">
                        <div className="flex gap-3">
                          <dt className="shrink-0 text-ink-faint">You ask</dt>
                          <dd className="min-w-0 text-ink-muted">
                            {s.example.q}
                          </dd>
                        </div>
                        <div className="flex gap-3">
                          <dt className="shrink-0 text-ink-faint">AI says</dt>
                          <dd className="min-w-0 text-risk-danger">
                            {s.example.a}
                          </dd>
                        </div>
                      </dl>
                      <p className="mt-4 border-t border-rule pt-3 text-[0.8125rem] leading-relaxed text-ink-muted">
                        {s.example.why}
                      </p>
                    </div>
                  )}

                  {s.compare && (
                    <div className="space-y-2">
                      {s.compare.map((c) => (
                        <div
                          key={c.q}
                          className="rounded-card border p-4"
                          style={{
                            borderColor: `var(--risk-${c.tone})`,
                            background: `var(--risk-${c.tone}-wash)`,
                          }}
                        >
                          <p className="font-mono text-[0.75rem] text-ink-muted">
                            {c.q}
                          </p>
                          <p className="mt-2 text-[0.8125rem] text-ink">
                            Next word candidates:{" "}
                            <span className="text-ink-muted">{c.spread}</span>
                          </p>
                          <p
                            className="mt-1.5 font-mono text-[0.75rem]"
                            style={{ color: `var(--risk-${c.tone})` }}
                          >
                            → the AI is {c.verdict}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>

        <Reveal>
          <p className="mx-auto mt-10 max-w-2xl text-center text-[0.9375rem] leading-relaxed text-ink-muted">
            That is the entire tool. It reads how sure the AI was while it was
            writing, and hands you a number before you trust the answer — using
            an AI running on your own computer, with nothing sent anywhere.
          </p>
        </Reveal>
      </div>
    </section>
  );
}

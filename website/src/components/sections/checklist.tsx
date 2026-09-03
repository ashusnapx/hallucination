"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { DELIVERABLES, STATUS_META } from "@/lib/proposal";
import { Reveal } from "@/components/ui/reveal";
import { cn } from "@/lib/utils";

/**
 * The project answered as the five questions an examiner actually asks, then
 * the full asked-vs-delivered table.
 *
 * Deliberately placed on the landing page rather than buried in the dashboard:
 * for a reviewer, "did it do what it said it would" is the first question, not
 * the last.
 */

const W_QUESTIONS = [
  {
    k: "What",
    q: "What was asked for?",
    a: "A system that predicts, in real time, whether a language model's answer is a hallucination — by reading the model's own internal signals rather than checking the answer against an outside source afterwards.",
  },
  {
    k: "Why",
    q: "Why does it matter?",
    a: "A wrong answer that sounds right is worse than no answer. In medicine a made-up dosage can harm someone; in law, fabricated case citations have led to real court sanctions. Existing tools only notice after the answer is already on screen.",
  },
  {
    k: "How",
    q: "How does it work?",
    a: "While the AI writes, it scores every word it might say next. When it knows something, one word wins clearly; when it is inventing, many words tie. We measure that spread, and if it is unclear we ask the same question again a few times and check whether the answers agree.",
  },
  {
    k: "Where",
    q: "Where does it run?",
    a: "Entirely on your own machine, through Ollama. Nothing is sent to any company. There is no API key, no bill, and no second AI grading the first — the model that answered is the only model involved.",
  },
  {
    k: "When",
    q: "When does it decide?",
    a: "Before you see the answer. The cheap check adds about 20 milliseconds to a generation that had to happen anyway; the slower check only runs on the questions where the cheap one was not conclusive.",
  },
];

const STATUS_ORDER = ["met", "partial", "changed", "missed"] as const;

export function Checklist() {
  const [open, setOpen] = useState<string | null>(null);

  const counts = STATUS_ORDER.map((s) => ({
    s,
    n: DELIVERABLES.filter((d) => d.status === s).length,
  }));

  return (
    <section className="border-t border-rule py-(--spacing-section)">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        <Reveal className="max-w-2xl">
          <span className="eyebrow">The brief</span>
          <h2 className="title mt-3">
            What was asked, and what we <em>actually built</em>
          </h2>
          <p className="mt-4 text-lede text-ink-muted">
            The project began with a written proposal. Here it is answered
            plainly — first as five questions, then line by line against every
            promise it made.
          </p>
        </Reveal>

        {/* The five W-questions */}
        <dl className="mt-12 grid gap-px overflow-hidden rounded-card border border-rule bg-rule sm:grid-cols-2 lg:grid-cols-3">
          {W_QUESTIONS.map((w) => (
            <div key={w.k} className="bg-paper p-6">
              <span className="eyebrow">{w.k}</span>
              <dt className="mt-2 font-display text-[1.125rem] leading-snug">
                {w.q}
              </dt>
              <dd className="mt-2.5 text-[0.875rem] leading-relaxed text-ink-muted">
                {w.a}
              </dd>
            </div>
          ))}
          <div className="flex flex-col justify-center bg-paper-sunken p-6">
            <span className="eyebrow">Scored</span>
            <p className="mt-2 text-[0.875rem] leading-relaxed text-ink-muted">
              Eleven things were promised. Two targets were missed, and they are
              labelled missed — a scorecard that only shows green is not a
              scorecard.
            </p>
            <div className="mt-4 flex flex-wrap gap-1.5">
              {counts.map(({ s, n }) => (
                <span
                  key={s}
                  className="inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-[0.6875rem]"
                  style={{
                    borderColor: `var(--risk-${STATUS_META[s].token})`,
                    color: `var(--risk-${STATUS_META[s].token})`,
                  }}
                >
                  <span className="font-mono font-medium">{n}</span>
                  {STATUS_META[s].label}
                </span>
              ))}
            </div>
          </div>
        </dl>

        {/* Asked vs delivered, line by line */}
        <div className="mt-4 overflow-hidden rounded-card border border-rule">
          <div className="hidden grid-cols-[1.1fr_1fr_1fr_auto] gap-4 border-b border-rule bg-paper-sunken px-5 py-2.5 sm:grid">
            {["What was asked", "Target set", "What we delivered", ""].map(
              (h) => (
                <span key={h} className="eyebrow">
                  {h}
                </span>
              ),
            )}
          </div>

          <ul>
            {DELIVERABLES.map((d) => {
              const meta = STATUS_META[d.status];
              const isOpen = open === d.id;
              return (
                <li key={d.id} className="border-b border-rule last:border-0">
                  <button
                    type="button"
                    onClick={() => setOpen(isOpen ? null : d.id)}
                    aria-expanded={isOpen}
                    className="flex w-full items-start gap-3 px-5 py-3.5 text-left transition-colors hover:bg-paper-sunken"
                  >
                    <span
                      className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                      style={{ background: `var(--risk-${meta.token})` }}
                      aria-hidden
                    />
                    <span className="grid min-w-0 flex-1 gap-1 sm:grid-cols-[1.1fr_1fr_1fr] sm:gap-4">
                      <span className="text-[0.875rem] font-medium text-ink">
                        {d.promised}
                      </span>
                      <span className="font-mono text-[0.75rem] text-ink-faint">
                        <span className="sm:hidden">asked for: </span>
                        {d.target}
                      </span>
                      <span className="font-mono text-[0.75rem] text-ink-muted">
                        <span className="sm:hidden">delivered: </span>
                        {d.actual}
                      </span>
                    </span>
                    <span
                      className="shrink-0 font-mono text-[0.6875rem]"
                      style={{ color: `var(--risk-${meta.token})` }}
                    >
                      {meta.label}
                    </span>
                    <ChevronDown
                      className={cn(
                        "mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-faint transition-transform duration-200",
                        isOpen && "rotate-180",
                      )}
                      aria-hidden
                    />
                  </button>
                  {isOpen && (
                    <p className="border-t border-rule bg-paper-sunken px-5 py-3.5 text-[0.8125rem] leading-relaxed text-ink-muted sm:pl-11">
                      {d.note}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>

        <p className="mt-3 text-[0.75rem] leading-relaxed text-ink-faint">
          Targets are transcribed from the submitted proposal and slide deck.
          Click any row to see why it landed where it did.
        </p>
      </div>
    </section>
  );
}

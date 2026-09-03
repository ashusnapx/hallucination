"use client";

import { motion, useReducedMotion } from "motion/react";
import { ArrowUpRight, Terminal } from "lucide-react";
import Link from "next/link";
import { LinkButton } from "@/components/ui/button";
import { CopyButton } from "@/components/ui/copy-button";
import { GITHUB_URL, INSTALL_CMD, RESULTS } from "@/lib/site";

/**
 * Above the fold: the claim, the install line, and the product's actual output.
 *
 * The specimen is a real measured example — llama3.2:3b answering "On a violin"
 * to a question about *Fiddler on the Roof*, scored 0.881 in 20ms of overhead.
 * Showing the instrument reading beats describing it, and it is the one thing
 * a black-box tool cannot put on its homepage.
 */
export function Hero() {
  const reduce = useReducedMotion();

  const rise = (delay: number) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 14 },
          animate: { opacity: 1, y: 0 },
          transition: {
            duration: 0.7,
            delay,
            ease: [0.22, 1, 0.36, 1] as const,
          },
        };

  return (
    <section
      id="top"
      className="relative overflow-hidden pt-32 pb-(--spacing-section) sm:pt-40"
    >
      {/* A faint engineering grid, faded out at the edges. Instrument, not decoration. */}
      <div
        aria-hidden
        className="grid-paper pointer-events-none absolute inset-0 opacity-50 [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,black,transparent)]"
      />

      <div className="relative mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        <motion.div {...rise(0)} className="flex justify-center">
          <Link
            href="/results"
            className="inline-flex items-center gap-2 rounded-pill border border-rule bg-paper-raised px-3 py-1.5 text-[0.75rem] text-ink-muted transition-colors hover:border-rule-strong hover:text-ink"
          >
            <span className="font-mono text-ink">AUROC {RESULTS.auroc}</span>
            <span className="text-ink-faint">
              on {RESULTS.n} questions, grouped CV
            </span>
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </motion.div>

        <motion.h1
          {...rise(0.06)}
          className="display mx-auto mt-7 max-w-4xl text-center text-balance"
        >
          Know it’s wrong <em>before</em> you show it
        </motion.h1>

        <motion.p
          {...rise(0.12)}
          className="mx-auto mt-6 max-w-xl text-center text-lede text-ink-muted text-pretty"
        >
          HalluciWatch scores how likely a local model’s answer is a
          hallucination — from the probabilities the model already computed
          while writing it. No API key, no judge model, no retrieval.
        </motion.p>

        <motion.div
          {...rise(0.18)}
          className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row"
        >
          <div className="flex items-center gap-1 rounded-pill border border-rule bg-paper-raised py-1 pl-4 pr-1">
            <Terminal
              className="h-3.5 w-3.5 shrink-0 text-ink-faint"
              aria-hidden
            />
            <code className="px-2 font-mono text-[0.8125rem] text-ink">
              {INSTALL_CMD}
            </code>
            <CopyButton value={INSTALL_CMD} label="Copy install command" />
          </div>
          <LinkButton href="/demo" size="lg">
            See it score a real answer
          </LinkButton>
        </motion.div>

        <motion.div {...rise(0.26)} className="mt-16">
          <Specimen />
        </motion.div>

        <motion.p
          {...rise(0.32)}
          className="mx-auto mt-5 max-w-lg text-center text-[0.8125rem] leading-relaxed text-ink-faint"
        >
          A real reading. It is <em>Fiddler on the Roof</em> — the model is
          fluent, confident and wrong, and the verdict cost 20ms on top of a
          generation that had to happen anyway.{" "}
          <a
            href={GITHUB_URL}
            className="underline underline-offset-2 hover:text-ink-muted"
          >
            Reproduce it
          </a>
          .
        </motion.p>
      </div>
    </section>
  );
}

/* The measured example, rendered as the CLI actually prints it. */
function Specimen() {
  return (
    <div className="mx-auto max-w-3xl overflow-hidden rounded-card border border-rule bg-paper-raised shadow-float">
      <div className="flex items-center gap-1.5 border-b border-rule px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-rule-strong" />
        <span className="h-2.5 w-2.5 rounded-full bg-rule-strong" />
        <span className="h-2.5 w-2.5 rounded-full bg-rule-strong" />
        <span className="ml-2 font-mono text-[0.6875rem] text-ink-faint">
          halluciwatch score
        </span>
      </div>

      <div className="space-y-3 px-4 py-5 font-mono text-[0.75rem] leading-relaxed sm:px-5 sm:text-[0.8125rem]">
        <div className="flex gap-3">
          <span className="shrink-0 text-ink-faint">Q</span>
          <span className="min-w-0 text-ink-muted">
            Where was the Fiddler in the musical’s title?
          </span>
        </div>
        <div className="flex gap-3">
          <span className="shrink-0 text-ink-faint">A</span>
          <span className="min-w-0 text-ink">
            <span className="rounded-[3px] bg-risk-danger-wash px-0.5">On</span>{" "}
            <span className="rounded-[3px] bg-risk-danger-wash px-0.5">a</span>{" "}
            <span className="rounded-[3px] bg-risk-caution-wash px-0.5">
              violin
            </span>
            .
          </span>
        </div>

        <div className="!mt-5 space-y-2 border-t border-rule pt-4">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <span className="w-14 shrink-0 text-[0.6875rem] text-ink-faint">
              risk
            </span>
            <div className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-paper-sunken sm:w-40">
              <div className="h-full w-[88%] rounded-full bg-risk-danger" />
            </div>
            <span className="text-ink">0.881</span>
            <span className="text-risk-danger">reject</span>
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-0.5">
            <span className="w-14 shrink-0 text-[0.6875rem] text-ink-faint">
              tiers
            </span>
            <span className="min-w-0 text-ink-muted">
              surface + token{" "}
              <span className="text-ink-faint">· sampling skipped</span>
            </span>
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-0.5">
            <span className="w-14 shrink-0 text-[0.6875rem] text-ink-faint">
              latency
            </span>
            <span className="min-w-0 text-ink-muted">
              1.12s{" "}
              <span className="text-ink-faint">(scoring overhead 0.02s)</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

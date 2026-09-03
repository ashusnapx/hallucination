"use client";

import { useState } from "react";
import { CodeBlock } from "@/components/ui/code-block";
import { LinkButton } from "@/components/ui/button";
import { GITHUB_URL } from "@/lib/site";
import { cn } from "@/lib/utils";
import { Reveal } from "@/components/ui/reveal";

const TABS = [
  {
    id: "cli",
    label: "CLI",
    language: "bash" as const,
    filename: "terminal",
    code: `# 1. a local model, through Ollama
brew install ollama && ollama serve
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# 2. the package
pip install "halluciwatch[all]"
halluciwatch doctor

# 3. score something
halluciwatch score "Who discovered penicillin?"`,
  },
  {
    id: "python",
    label: "Python",
    language: "python" as const,
    filename: "score.py",
    code: `from halluciwatch import HallucinationDetector

with HallucinationDetector() as detector:
    report = detector.score("Who discovered penicillin?")

    print(report.risk)         # 0.0-1.0, calibrated
    print(report.decision)     # accept | review | reject | abstain
    print(report.answer)
    print(report.top_factors)  # what moved the score
    print(report.clusters)     # distinct answers, if it escalated`,
  },
  {
    id: "http",
    label: "HTTP",
    language: "bash" as const,
    filename: "terminal",
    code: `halluciwatch serve --model-dir models/llama3.2-3b

curl -s localhost:8000/score \\
  -H 'content-type: application/json' \\
  -d '{"question":"Who invented the telephone?"}'

# GET /features   documents every feature and its tier
# POST /score/stream  server-sent events, answer first`,
  },
  {
    id: "train",
    label: "Train your own",
    language: "bash" as const,
    filename: "terminal",
    code: `# the detector is only calibrated for the model it saw
make build     # generate a labelled corpus (resumable)
make train     # fit + calibrate, prints cross-validated metrics
make ablate    # what does each tier buy on YOUR model?
make report    # regenerate RESULTS.md from the artefacts`,
  },
];

export function Install() {
  const [active, setActive] = useState(TABS[0].id);
  const tab = TABS.find((t) => t.id === active)!;

  return (
    <section className="border-t border-rule py-(--spacing-section)">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        <Reveal className="max-w-2xl">
          <span className="eyebrow">Deliverable</span>
          <h2 className="title mt-3">
            Runs on your <em>machine</em>
          </h2>
          <p className="mt-4 text-lede text-ink-muted">
            An open-source library, a CLI and an HTTP API. No API keys, no judge
            model, no retrieval index — the model lives in Ollama rather than in
            your process.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)] lg:gap-16">
          <Reveal className="min-w-0">
            <div>
              <h3 className="font-display text-heading">What you get</h3>

              <dl className="mt-5 space-y-4 border-t border-rule pt-5">
                {[
                  [
                    "No API keys",
                    "Nothing leaves the machine. No provider, no bill, no rate limit.",
                  ],
                  [
                    "No judge model",
                    "The scored model is the only model. There is no second LLM grading the first.",
                  ],
                  [
                    "Apache-2.0",
                    "Fork it, vendor it, publish a paper disagreeing with it.",
                  ],
                ].map(([term, def]) => (
                  <div key={term}>
                    <dt className="text-[0.875rem] font-medium text-ink">
                      {term}
                    </dt>
                    <dd className="mt-1 text-[0.875rem] leading-relaxed text-ink-muted">
                      {def}
                    </dd>
                  </div>
                ))}
              </dl>

              <LinkButton
                href={GITHUB_URL}
                target="_blank"
                rel="noreferrer noopener"
                variant="secondary"
                className="mt-7"
              >
                Read the source
              </LinkButton>
            </div>
          </Reveal>

          <div className="min-w-0">
            <div
              role="tablist"
              aria-label="Integration examples"
              className="flex flex-wrap gap-1"
            >
              {TABS.map((t) => (
                <button
                  key={t.id}
                  role="tab"
                  id={`tab-${t.id}`}
                  aria-selected={active === t.id}
                  aria-controls={`panel-${t.id}`}
                  onClick={() => setActive(t.id)}
                  className={cn(
                    "rounded-pill px-3 py-1.5 text-[0.8125rem] transition-colors",
                    active === t.id
                      ? "bg-ink text-paper"
                      : "text-ink-muted hover:bg-paper-sunken hover:text-ink",
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div
              role="tabpanel"
              id={`panel-${tab.id}`}
              aria-labelledby={`tab-${tab.id}`}
              className="mt-3"
            >
              <CodeBlock
                code={tab.code}
                language={tab.language}
                filename={tab.filename}
              />
            </div>

            <p className="mt-3 text-[0.75rem] leading-relaxed text-ink-faint">
              A shipped detector is calibrated for the model it was trained on.
              Point it at a different model and the probabilities stop meaning
              what they say — <code className="font-mono">make train</code> is
              the fix, and it takes about an hour on a laptop.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

import { GitHubIcon } from "@/components/ui/icons";
import { GITHUB_URL, PYPI_URL, PAPER_URL, PROJECT_CREDITS } from "@/lib/site";
import Link from "next/link";
import { Mark } from "./nav";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "Live demo", href: "/demo" },
      { label: "Results & dashboard", href: "/dashboard" },
    ],
  },
  {
    title: "Source",
    links: [
      { label: "GitHub", href: GITHUB_URL },
      { label: "PyPI", href: PYPI_URL },
      { label: "Benchmark report", href: PAPER_URL },
    ],
  },
  {
    title: "Reading",
    links: [
      {
        label: "Semantic entropy (Nature 2024)",
        href: "https://www.nature.com/articles/s41586-024-07421-0",
      },
      { label: "SelfCheckGPT", href: "https://arxiv.org/abs/2303.08896" },
      {
        label: "P(True) — Kadavath et al.",
        href: "https://arxiv.org/abs/2207.05221",
      },
      { label: "LM-Polygraph", href: "https://github.com/IINemo/lm-polygraph" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter) py-16">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div>
            <Link href="/" className="flex items-center gap-2">
              <Mark />
              <span className="font-display text-[1.0625rem] tracking-tight">
                HalluciWatch
              </span>
            </Link>
            <p className="mt-3 max-w-xs text-[0.8125rem] leading-relaxed text-ink-muted">
              Calibrated hallucination risk for local LLMs, read from the
              model’s own token probabilities.
            </p>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-4 inline-flex items-center gap-1.5 text-[0.8125rem] text-ink-muted transition-colors hover:text-ink"
            >
              <GitHubIcon className="h-3.5 w-3.5" />
              Apache-2.0 on GitHub
            </a>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h3 className="eyebrow">{col.title}</h3>
              <ul className="mt-3.5 space-y-2">
                {col.links.map((l) => (
                  <li key={l.label}>
                    {l.href.startsWith("http") ? (
                      <a
                        href={l.href}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="text-[0.8125rem] text-ink-muted transition-colors hover:text-ink"
                      >
                        {l.label}
                      </a>
                    ) : (
                      <Link
                        href={l.href}
                        className="text-[0.8125rem] text-ink-muted transition-colors hover:text-ink"
                      >
                        {l.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Academic attribution. The source documents carry no names, so these
            are placeholders in src/lib/site.ts for the author to fill in. */}
        <dl className="mt-12 grid gap-x-8 gap-y-4 border-t border-rule pt-6 sm:grid-cols-2 lg:grid-cols-4">
          {PROJECT_CREDITS.map((c) => (
            <div key={c.label}>
              <dt className="eyebrow">{c.label}</dt>
              <dd className="mt-1 text-[0.8125rem] text-ink-muted">
                {c.value}
              </dd>
            </div>
          ))}
        </dl>

        <div className="mt-10 flex flex-col gap-2 border-t border-rule pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-[0.6875rem] text-ink-faint">
            Every number on this site is measured, not estimated.
          </p>
          <p className="font-mono text-[0.6875rem] text-ink-faint">
            Apache-2.0
          </p>
        </div>
      </div>
    </footer>
  );
}

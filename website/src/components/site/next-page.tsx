import Link from "next/link";
import { ArrowRight } from "lucide-react";

/**
 * The forward link at the foot of each sub-page.
 *
 * Splitting a single scroll into routes costs the reader the momentum a long
 * page gives for free, so every page ends by naming the next one explicitly.
 */
export function NextPage({
  href,
  eyebrow,
  title,
  blurb,
}: {
  href: string;
  eyebrow: string;
  title: string;
  blurb: string;
}) {
  return (
    <div className="border-t border-rule">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter) py-14">
        <Link
          href={href}
          className="group flex flex-col gap-4 rounded-card border border-rule bg-paper-raised p-6 transition-colors hover:border-rule-strong sm:flex-row sm:items-center sm:justify-between sm:p-8"
        >
          <div className="min-w-0">
            <span className="eyebrow">{eyebrow}</span>
            <h2 className="mt-2 font-display text-heading">{title}</h2>
            <p className="mt-1.5 max-w-xl text-[0.875rem] leading-relaxed text-ink-muted">
              {blurb}
            </p>
          </div>
          <ArrowRight className="h-5 w-5 shrink-0 text-ink-faint transition-transform duration-300 ease-[var(--ease-out-soft)] group-hover:translate-x-1 group-hover:text-ink" />
        </Link>
      </div>
    </div>
  );
}

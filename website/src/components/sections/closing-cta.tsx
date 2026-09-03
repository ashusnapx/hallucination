import { LinkButton } from "@/components/ui/button";
import { CopyButton } from "@/components/ui/copy-button";
import { Reveal } from "@/components/ui/reveal";
import { GITHUB_URL, INSTALL_CMD } from "@/lib/site";

export function ClosingCta() {
  return (
    <section className="border-t border-rule py-(--spacing-section)">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="title text-balance">
            Point it at your own model and <em>disagree with us</em>
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-lede text-ink-muted text-pretty">
            Every measurement on this site is reproducible with four make
            targets. If the cascade does not pay off on your model, the ablation
            will say so.
          </p>

          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <div className="flex items-center gap-1 rounded-pill border border-rule bg-paper-raised py-1 pl-4 pr-1">
              <code className="px-2 font-mono text-[0.8125rem] text-ink">
                {INSTALL_CMD}
              </code>
              <CopyButton value={INSTALL_CMD} label="Copy install command" />
            </div>
            <LinkButton
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer noopener"
              size="lg"
              variant="secondary"
            >
              Read the source
            </LinkButton>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

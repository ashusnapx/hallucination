import { Reveal } from "@/components/ui/reveal";

/**
 * The masthead each sub-page opens with.
 *
 * Sub-pages need more presence at the top than a section does inside a scroll —
 * there is no hero above them to establish the page, so the eyebrow and title
 * carry that alone.
 */
export function PageHeader({
  eyebrow,
  title,
  lede,
  meta,
}: {
  eyebrow: string;
  /** Wrap the emphasised span in <em> for the italic serif accent. */
  title: React.ReactNode;
  lede: React.ReactNode;
  /** Optional key/value strip: the measurement conditions, model, dataset. */
  meta?: { label: string; value: string }[];
}) {
  return (
    <div className="border-b border-rule pt-32 pb-12 sm:pt-40 sm:pb-16">
      <div className="mx-auto max-w-(--container-wide) px-(--spacing-gutter)">
        <Reveal>
          <span className="eyebrow">{eyebrow}</span>
          <h1 className="title mt-3 max-w-3xl text-balance">{title}</h1>
          <p className="mt-5 max-w-2xl text-lede text-ink-muted text-pretty">
            {lede}
          </p>

          {meta && meta.length > 0 && (
            <dl className="mt-8 flex flex-wrap gap-x-8 gap-y-3 border-t border-rule pt-5">
              {meta.map((m) => (
                <div key={m.label}>
                  <dt className="eyebrow">{m.label}</dt>
                  <dd className="mt-1 font-mono text-[0.8125rem] text-ink">
                    {m.value}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </Reveal>
      </div>
    </div>
  );
}

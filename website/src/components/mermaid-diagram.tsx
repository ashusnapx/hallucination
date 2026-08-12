"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Loader2, Maximize2, X } from "lucide-react";

interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

/**
 * Renders a Mermaid definition to inline SVG.
 *
 * Mermaid is imported lazily (client-only) because it touches `document` at
 * module scope and would break the server render.
 */
export function MermaidDiagram({ chart, className = "" }: MermaidDiagramProps) {
  const reactId = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [zoomed, setZoomed] = useState(false);
  const renderToken = useRef(0);

  useEffect(() => {
    if (!chart?.trim()) {
      setSvg("");
      return;
    }

    const token = ++renderToken.current;
    let cancelled = false;

    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;

        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: "base",
          fontFamily: "var(--font-sans), ui-sans-serif, system-ui",
          flowchart: {
            curve: "basis",
            padding: 18,
            nodeSpacing: 46,
            rankSpacing: 58,
            useMaxWidth: true,
            htmlLabels: true,
          },
          themeVariables: {
            background: "transparent",
            primaryColor: "#16182e",
            primaryTextColor: "#e5e7ff",
            primaryBorderColor: "#818cf8",
            lineColor: "#6366f1",
            secondaryColor: "#1b1340",
            tertiaryColor: "#111225",
            mainBkg: "#16182e",
            nodeBorder: "#818cf8",
            clusterBkg: "rgba(99,102,241,0.06)",
            clusterBorder: "rgba(129,140,248,0.35)",
            titleColor: "#c7d2fe",
            edgeLabelBackground: "#0d0f1c",
            fontSize: "13px",
          },
        });

        // `render` throws on malformed definitions — catch and show the source.
        const { svg: out } = await mermaid.render(`mmd-${reactId}-${token}`, chart);
        if (!cancelled && token === renderToken.current) {
          setSvg(out);
          setError(null);
        }
      } catch (e) {
        if (!cancelled && token === renderToken.current) {
          setError(e instanceof Error ? e.message : "Failed to render diagram");
          setSvg("");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [chart, reactId]);

  if (!chart?.trim()) return null;

  if (error) {
    return (
      <div className="rounded-xl border border-amber-500/25 bg-amber-500/5 p-4">
        <p className="text-xs font-medium text-amber-300">
          Diagram could not be rendered — showing the source instead.
        </p>
        <pre className="mt-3 max-h-64 overflow-auto rounded-lg bg-black/40 p-3 font-[family-name:var(--font-geist-mono)] text-[11px] leading-relaxed text-muted-foreground">
          {chart}
        </pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="flex h-48 items-center justify-center gap-2 rounded-xl border border-border/50 bg-muted/20 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Drawing flowchart…
      </div>
    );
  }

  return (
    <>
      <div className={`group relative ${className}`}>
        <button
          type="button"
          onClick={() => setZoomed(true)}
          aria-label="Expand diagram"
          className="absolute top-3 right-3 z-10 rounded-lg border border-border/60 bg-background/80 p-2 opacity-0 backdrop-blur transition group-hover:opacity-100 hover:border-primary/50 hover:text-primary focus-visible:opacity-100"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
        <div
          className="mermaid-host overflow-x-auto rounded-xl border border-border/50 bg-[oklch(0.11_0.015_264)] p-4 sm:p-6"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      </div>

      {zoomed && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4 backdrop-blur-sm"
          onClick={() => setZoomed(false)}
          role="dialog"
          aria-modal="true"
        >
          <button
            type="button"
            aria-label="Close diagram"
            className="absolute top-5 right-5 rounded-lg border border-white/15 bg-white/5 p-2.5 text-white/80 transition hover:bg-white/10"
            onClick={() => setZoomed(false)}
          >
            <X className="h-4 w-4" />
          </button>
          <div
            className="mermaid-host max-h-[90vh] w-full max-w-6xl overflow-auto rounded-2xl border border-white/10 bg-[oklch(0.11_0.015_264)] p-8"
            onClick={(e) => e.stopPropagation()}
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        </div>
      )}
    </>
  );
}

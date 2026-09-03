import { CopyButton } from "./copy-button";
import { cn } from "@/lib/utils";

/**
 * A terminal-style code block.
 *
 * Highlighting is done with a tiny token pass rather than a syntax-highlighting
 * dependency: the snippets on this page are short and known, and shipping Shiki
 * to colour six of them is not a trade worth making.
 */
export function CodeBlock({
  code,
  language = "bash",
  filename,
  className,
}: {
  code: string;
  language?: "bash" | "python" | "json" | "text";
  filename?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-card border border-rule bg-paper-sunken",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-rule px-3.5 py-2">
        <span className="font-mono text-[0.6875rem] tracking-wide text-ink-faint">
          {filename ?? language}
        </span>
        <CopyButton value={code} />
      </div>
      <pre className="overflow-x-auto px-3.5 py-3.5 text-[0.8125rem] leading-[1.7]">
        <code className="font-mono">{highlight(code, language)}</code>
      </pre>
    </div>
  );
}

const PY_KEYWORDS =
  /\b(from|import|as|with|def|class|return|if|else|elif|for|in|while|try|except|print|True|False|None|and|or|not)\b/;

function highlight(code: string, language: string) {
  return code.split("\n").map((line, i) => (
    <span key={i} className="block">
      {highlightLine(line, language)}
    </span>
  ));
}

function highlightLine(line: string, language: string) {
  // Whole-line cases first.
  if (language === "bash" && /^\s*#/.test(line)) {
    return <span className="text-ink-faint">{line}</span>;
  }
  if (language === "python" && /^\s*#/.test(line)) {
    return <span className="text-ink-faint">{line}</span>;
  }

  const parts = line.split(/("[^"]*"|'[^']*'|\s+)/).filter((p) => p !== "");

  return parts.map((part, i) => {
    if (/^["']/.test(part)) {
      return (
        <span key={i} className="text-risk-safe">
          {part}
        </span>
      );
    }
    if (language === "python" && PY_KEYWORDS.test(part)) {
      return (
        <span key={i} className="text-accent">
          {part}
        </span>
      );
    }
    if (
      language === "bash" &&
      /^(halluciwatch|ollama|pip|make|curl|brew|cd)$/.test(part)
    ) {
      return (
        <span key={i} className="text-accent">
          {part}
        </span>
      );
    }
    if (/^-{1,2}[a-z]/.test(part)) {
      return (
        <span key={i} className="text-ink-muted">
          {part}
        </span>
      );
    }
    if (/^[\d.]+$/.test(part)) {
      return (
        <span key={i} className="text-risk-caution">
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

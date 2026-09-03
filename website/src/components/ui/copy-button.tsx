"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

/** Copy-to-clipboard with a state that resets itself. */
export function CopyButton({
  value,
  className,
  label = "Copy",
}: {
  value: string;
  className?: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const t = setTimeout(() => setCopied(false), 1600);
    return () => clearTimeout(t);
  }, [copied]);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      // Clipboard is unavailable over plain http on some browsers; failing
      // silently is better than an error toast for a convenience affordance.
    }
  }, [value]);

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={copied ? "Copied" : label}
      className={cn(
        "inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-faint",
        "transition-colors duration-150 hover:bg-paper-sunken hover:text-ink",
        className,
      )}
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-risk-safe" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

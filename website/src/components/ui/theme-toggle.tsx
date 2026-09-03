"use client";

import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";

/**
 * Theme toggle with no mounted-state effect.
 *
 * The usual next-themes pattern sets a `mounted` flag in an effect to avoid a
 * hydration mismatch on the icon. React 19 flags that as a cascading render,
 * and it is avoidable: render both icons and let CSS pick, since the `.dark`
 * class is already on <html> before paint. No state, no flash, no effect.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label="Toggle colour theme"
      className="inline-flex h-8 w-8 items-center justify-center rounded-pill text-ink-muted transition-colors duration-150 hover:bg-paper-sunken hover:text-ink"
    >
      <Moon className="h-4 w-4 dark:hidden" aria-hidden />
      <Sun className="hidden h-4 w-4 dark:block" aria-hidden />
    </button>
  );
}

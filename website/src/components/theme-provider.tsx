"use client";

import { ThemeProvider as NextThemes } from "next-themes";

/** Light-first. `disableTransitionOnChange` avoids every element easing at
 *  once when the theme flips, which reads as lag rather than polish. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemes
      attribute="class"
      defaultTheme="light"
      enableSystem
      disableTransitionOnChange
    >
      {children}
    </NextThemes>
  );
}

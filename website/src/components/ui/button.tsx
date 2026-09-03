import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  // Ink-on-paper. The primary action is the darkest thing on the page, which
  // is a stronger affordance here than any accent colour would be.
  primary: "bg-ink text-paper hover:bg-ink/88 shadow-card",
  secondary:
    "bg-paper-raised text-ink border border-rule hover:border-rule-strong hover:bg-paper-sunken",
  ghost: "text-ink-muted hover:text-ink hover:bg-paper-sunken",
};

const SIZES: Record<Size, string> = {
  sm: "h-8 px-3 text-[0.8125rem] gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-12 px-6 text-[0.9375rem] gap-2",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-pill font-medium",
        "transition-[background-color,border-color,color,opacity] duration-200 ease-[var(--ease-out-soft)]",
        "disabled:pointer-events-none disabled:opacity-45",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export const LinkButton = React.forwardRef<
  HTMLAnchorElement,
  React.AnchorHTMLAttributes<HTMLAnchorElement> & {
    variant?: Variant;
    size?: Size;
  }
>(({ className, variant = "primary", size = "md", ...props }, ref) => (
  <a
    ref={ref}
    className={cn(
      "inline-flex shrink-0 items-center justify-center rounded-pill font-medium",
      "transition-[background-color,border-color,color,opacity] duration-200 ease-[var(--ease-out-soft)]",
      VARIANTS[variant],
      SIZES[size],
      className,
    )}
    {...props}
  />
));
LinkButton.displayName = "LinkButton";

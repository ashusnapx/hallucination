"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { GitHubIcon } from "@/components/ui/icons";
import { GITHUB_URL } from "@/lib/site";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/demo", label: "Live demo" },
  { href: "/dashboard", label: "Results" },
];

/**
 * A floating pill header. It detaches from the top edge once the page scrolls,
 * which keeps the hero uninterrupted at rest and gives the bar a surface to sit
 * on once there is content behind it.
 */
export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-(--spacing-gutter) pt-3">
      <nav
        className={cn(
          "mx-auto flex max-w-(--container-wide) items-center gap-3 rounded-pill px-4 py-2.5",
          "transition-[background-color,border-color,box-shadow] duration-300 ease-[var(--ease-out-soft)]",
          scrolled
            ? "border border-rule bg-paper/85 shadow-card backdrop-blur-xl"
            : "border border-transparent",
        )}
      >
        <Link
          href="/"
          className="flex shrink-0 items-center gap-2"
          aria-label="HalluciWatch home"
        >
          <Mark />
          <span className="font-display text-[1.0625rem] tracking-tight">
            HalluciWatch
          </span>
        </Link>

        <ul className="ml-4 hidden items-center gap-1 md:flex">
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <li key={l.href}>
                <Link
                  href={l.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "rounded-pill px-2.5 py-1.5 text-[0.8125rem] transition-colors",
                    active
                      ? "bg-paper-sunken text-ink"
                      : "text-ink-muted hover:bg-paper-sunken hover:text-ink",
                  )}
                >
                  {l.label}
                </Link>
              </li>
            );
          })}
        </ul>

        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer noopener"
            aria-label="GitHub repository"
            className="inline-flex h-8 w-8 items-center justify-center rounded-pill text-ink-muted transition-colors hover:bg-paper-sunken hover:text-ink"
          >
            <GitHubIcon className="h-4 w-4" />
          </a>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            className="inline-flex h-8 w-8 items-center justify-center rounded-pill text-ink-muted transition-colors hover:bg-paper-sunken hover:text-ink md:hidden"
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </nav>

      {open && (
        <div className="mx-auto mt-2 max-w-(--container-wide) rounded-card border border-rule bg-paper/95 p-2 shadow-float backdrop-blur-xl md:hidden">
          <ul>
            {LINKS.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  onClick={() => setOpen(false)}
                  aria-current={pathname === l.href ? "page" : undefined}
                  className={cn(
                    "block rounded-md px-3 py-2.5 text-[0.875rem] transition-colors",
                    pathname === l.href
                      ? "bg-paper-sunken text-ink"
                      : "text-ink-muted hover:bg-paper-sunken hover:text-ink",
                  )}
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </header>
  );
}

/** A four-step uncertainty ramp — the product's own signal as a monogram. */
export function Mark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      className={cn("h-[18px] w-[18px]", className)}
      aria-hidden
    >
      {[0, 1, 2, 3].map((i) => (
        <rect
          key={i}
          x={1 + i * 5}
          y={14 - i * 4}
          width={3.4}
          height={4 + i * 4}
          rx={1}
          fill="currentColor"
          opacity={0.35 + i * 0.22}
        />
      ))}
    </svg>
  );
}

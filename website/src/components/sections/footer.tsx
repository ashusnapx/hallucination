"use client";

import { motion } from "motion/react";
import { Globe, ExternalLink, BookOpen, Heart } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { GITHUB_URL, INSTALL_CMD } from "@/lib/constants";

interface FooterLink {
  label: string;
  href: string;
  scroll?: boolean;
  external?: boolean;
}

const footerLinks: Record<string, FooterLink[]> = {
  Product: [
    { label: "Features", href: "#features", scroll: true },
    { label: "Benchmarks", href: "#benchmarks", scroll: true },
    { label: "Documentation", href: "#docs", scroll: true },
    { label: "Interactive Demo", href: "#demo", scroll: true },
  ],
  Resources: [
    { label: "GitHub Repository", href: GITHUB_URL, external: true },
    { label: "PyPI Package", href: "https://pypi.org/project/halluciwatch/", external: true },
    { label: "API Reference", href: GITHUB_URL, external: true },
    { label: "Research Papers", href: "#benchmarks", scroll: true },
  ],
  Community: [
    { label: "GitHub Discussions", href: GITHUB_URL, external: true },
    { label: "Contributing Guide", href: GITHUB_URL, external: true },
    { label: "Report Issues", href: `${GITHUB_URL}/issues`, external: true },
    { label: "Changelog", href: GITHUB_URL, external: true },
  ],
  Legal: [
    { label: "Apache 2.0 License", href: `${GITHUB_URL}/blob/main/LICENSE`, external: true },
    { label: "Privacy Policy", href: "#", scroll: true },
    { label: "Terms of Use", href: "#", scroll: true },
  ],
};

export function Footer() {
  const handleClick = (href: string, scroll?: boolean, external?: boolean) => {
    if (external) {
      window.open(href, "_blank", "noopener,noreferrer");
    } else if (scroll) {
      const id = href.replace("#", "");
      const el = document.getElementById(id);
      if (el) {
        const offset = 80;
        const y = el.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top: y, behavior: "smooth" });
      }
    }
  };

  return (
    <footer className="relative border-t border-border/50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-12 py-16 sm:grid-cols-2 lg:grid-cols-5">
          {/* Brand */}
          <div className="lg:col-span-2">
            <div className="flex items-center gap-2.5">
              <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                <div className="h-3 w-3 rounded-full bg-primary pulse-glow" />
                <div className="absolute inset-0 rounded-lg border border-primary/20" />
              </div>
              <span className="font-[family-name:var(--font-display)] text-lg font-bold tracking-tight">
                HalluciWatch
              </span>
            </div>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted-foreground">
              Real-time hallucination risk detection for Large Language Models.
              Predict hallucinations before they happen by reading internal
              neural signals.
            </p>

            {/* Install command with copy */}
            <div className="mt-6 flex items-center gap-2">
              <code className="rounded-lg bg-muted px-3 py-1.5 font-[family-name:var(--font-geist-mono)] text-xs">
                {INSTALL_CMD}
              </code>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(INSTALL_CMD);
                }}
                className="rounded-lg bg-muted px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted/80 hover:text-foreground"
                title="Copy to clipboard"
              >
                📋
              </button>
            </div>

            <div className="mt-6 flex items-center gap-4">
              <button
                onClick={() => window.open(GITHUB_URL, "_blank")}
                className="text-muted-foreground transition-colors hover:text-foreground"
                title="GitHub"
              >
                <Globe className="h-5 w-5" />
              </button>
              <button
                onClick={() => window.open(`${GITHUB_URL}`, "_blank")}
                className="text-muted-foreground transition-colors hover:text-foreground"
                title="Documentation"
              >
                <BookOpen className="h-5 w-5" />
              </button>
              <button
                onClick={() => window.open("https://pypi.org/project/halluciwatch/", "_blank")}
                className="text-muted-foreground transition-colors hover:text-foreground"
                title="PyPI"
              >
                <ExternalLink className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold">
                {category}
              </h3>
              <ul className="mt-4 space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <button
                      onClick={() => handleClick(link.href, link.scroll, link.external)}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                      {link.external && (
                        <ExternalLink className="ml-1 inline h-3 w-3" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <Separator />

        <div className="flex flex-col items-center justify-between gap-4 py-8 sm:flex-row">
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} HalluciWatch. Apache 2.0 License.
          </p>
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            Built with <Heart className="h-3.5 w-3.5 text-red-400" /> for AI
            safety
          </p>
        </div>
      </div>
    </footer>
  );
}

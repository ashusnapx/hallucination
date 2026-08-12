"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { Menu, Globe, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { scrollTo, GITHUB_URL } from "@/lib/constants";

const navLinks = [
  { label: "Features", href: "features" },
  { label: "How It Works", href: "how-it-works" },
  { label: "Benchmarks", href: "benchmarks" },
  { label: "Docs", href: "docs" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);

  const handleNav = (id: string) => {
    scrollTo(id);
    setOpen(false);
  };

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="fixed top-0 left-0 right-0 z-50"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="glass-card mt-4 rounded-2xl px-6 py-3">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                <div className="h-3 w-3 rounded-full bg-primary pulse-glow" />
                <div className="absolute inset-0 rounded-lg border border-primary/20" />
              </div>
              <span className="font-[family-name:var(--font-display)] text-lg font-bold tracking-tight">
                HalluciWatch
              </span>
            </Link>

            <nav className="hidden items-center gap-1 md:flex">
              {navLinks.map((link) => (
                <button
                  key={link.href}
                  onClick={() => handleNav(link.href)}
                  className="rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
                >
                  {link.label}
                </button>
              ))}
            </nav>

            <div className="hidden items-center gap-3 md:flex">
              <Link
                href={GITHUB_URL}
                target="_blank"
                rel="noreferrer"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                <Globe className="h-5 w-5" />
              </Link>
              <Button
                size="sm"
                className="rounded-xl font-semibold"
                onClick={() => scrollTo("docs")}
              >
                Get Started
                <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
              </Button>
            </div>

            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon"
                    className="rounded-xl md:hidden"
                  />
                }
              >
                <Menu className="h-5 w-5" />
              </SheetTrigger>
              <SheetContent side="right" className="w-72">
                <div className="flex flex-col gap-6 pt-8">
                  {navLinks.map((link) => (
                    <button
                      key={link.href}
                      onClick={() => handleNav(link.href)}
                      className="text-left text-lg font-medium text-foreground transition-colors hover:text-primary"
                    >
                      {link.label}
                    </button>
                  ))}
                  <Button
                    className="mt-4 rounded-xl font-semibold"
                    onClick={() => {
                      scrollTo("docs");
                      setOpen(false);
                    }}
                  >
                    Get Started
                    <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
                  </Button>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </motion.header>
  );
}

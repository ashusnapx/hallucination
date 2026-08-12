"use client";

import { motion } from "motion/react";
import { ArrowRight, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { scrollTo, GITHUB_URL, INSTALL_CMD } from "@/lib/constants";

export function CTA() {
  return (
    <section className="relative py-24 sm:py-32 overflow-hidden">
      <div className="absolute inset-0">
        <div className="absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/10 blur-[120px]" />
      </div>

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.7 }}
          className="glass-card glow-border mx-auto max-w-3xl rounded-3xl p-8 sm:p-12 text-center"
        >
          <Badge
            variant="secondary"
            className="mb-6 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm font-medium"
          >
            Open Source & Free
          </Badge>

          <h2 className="font-[family-name:var(--font-display)] text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            Start detecting hallucinations{" "}
            <span className="gradient-text">today</span>
          </h2>

          <p className="mx-auto mt-6 max-w-xl text-lg text-muted-foreground">
            Install HalluciWatch in seconds. Works with any HuggingFace-compatible
            LLM. No external APIs required.
          </p>

          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Button
              size="lg"
              className="group rounded-2xl px-8 py-6 text-base font-semibold shadow-lg shadow-primary/25"
              onClick={() => scrollTo("docs")}
            >
              Get Started
              <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="rounded-2xl px-8 py-6 text-base font-semibold"
              onClick={() => window.open(GITHUB_URL, "_blank")}
            >
              <Globe className="mr-2 h-4 w-4" />
              View Source
            </Button>
          </div>

          <div className="mt-8 font-[family-name:var(--font-geist-mono)] text-sm text-muted-foreground">
            {INSTALL_CMD}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

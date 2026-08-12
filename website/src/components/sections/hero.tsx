"use client";

import { useEffect, useRef } from "react";
import { motion } from "motion/react";
import gsap from "gsap";
import { ArrowRight, Sparkles, Zap, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { scrollTo, GITHUB_URL } from "@/lib/constants";

export function Hero() {
  const headlineRef = useRef<HTMLHeadingElement>(null);
  const wordsRef = useRef<(HTMLSpanElement | null)[]>([]);

  useEffect(() => {
    if (!headlineRef.current) return;
    const words = wordsRef.current.filter(Boolean);
    gsap.fromTo(
      words,
      { opacity: 0, y: 40, rotateX: -40 },
      {
        opacity: 1,
        y: 0,
        rotateX: 0,
        duration: 0.8,
        stagger: 0.08,
        ease: "power3.out",
        delay: 0.3,
      }
    );
  }, []);

  const headlineWords = [
    "Predict",
    "Hallucinations",
    "Before",
    "They",
    "Happen",
  ];

  return (
    <section className="relative min-h-screen overflow-hidden pt-32 pb-20">
      <div className="aurora absolute inset-0" />
      <div className="grid-pattern absolute inset-0 opacity-40" />

      <motion.div
        animate={{ y: [0, -20, 0], x: [0, 10, 0] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-1/4 left-[15%] h-72 w-72 rounded-full bg-primary/10 blur-3xl"
      />
      <motion.div
        animate={{ y: [0, 15, 0], x: [0, -15, 0] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 2 }}
        className="absolute bottom-1/4 right-[10%] h-96 w-96 rounded-full bg-chart-2/10 blur-3xl"
      />

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Badge
              variant="secondary"
              className="mb-8 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm font-medium"
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5 text-primary" />
              Open Source — pip install halluciwatch
            </Badge>
          </motion.div>

          <h1
            ref={headlineRef}
            className="font-[family-name:var(--font-display)] mx-auto max-w-5xl text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl md:text-7xl lg:text-8xl"
            style={{ perspective: "1000px" }}
          >
            {headlineWords.map((word, i) => (
              <span
                key={i}
                ref={(el) => { wordsRef.current[i] = el; }}
                className={`mr-[0.3em] inline-block ${i === 1 ? "gradient-text" : ""}`}
                style={{ opacity: 0 }}
              >
                {word}
              </span>
            ))}
          </h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 1 }}
            className="mt-8 max-w-2xl text-lg leading-relaxed text-muted-foreground sm:text-xl md:text-2xl"
          >
            A real-time hallucination risk detection system that reads internal
            neural signals during LLM generation — before the answer is shown to
            the user.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 1.2 }}
            className="mt-10 flex flex-col items-center gap-4 sm:flex-row"
          >
            <Button
              size="lg"
              className="group rounded-2xl px-8 py-6 text-base font-semibold shadow-lg shadow-primary/25 transition-all hover:shadow-xl hover:shadow-primary/30"
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
              View on GitHub
            </Button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 1.4 }}
            className="mt-16 grid grid-cols-3 gap-8 md:gap-16"
          >
            {[
              { icon: Zap, value: "<50ms", label: "Added Latency" },
              { icon: Shield, value: ">0.90", label: "AUC-ROC Score" },
              { icon: Sparkles, value: "35K+", label: "Training Samples" },
            ].map(({ icon: Icon, value, label }) => (
              <div key={label} className="flex flex-col items-center">
                <Icon className="mb-2 h-5 w-5 text-primary/60" />
                <span className="font-[family-name:var(--font-display)] text-2xl font-bold sm:text-3xl">
                  {value}
                </span>
                <span className="mt-1 text-xs text-muted-foreground sm:text-sm">
                  {label}
                </span>
              </div>
            ))}
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, delay: 1.6, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto mt-20 max-w-4xl"
        >
          <div className="gradient-border">
            <div className="glass-card rounded-2xl p-6 sm:p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="h-3 w-3 rounded-full bg-red-500" />
                <div className="h-3 w-3 rounded-full bg-yellow-500" />
                <div className="h-3 w-3 rounded-full bg-green-500" />
                <span className="ml-2 font-[family-name:var(--font-geist-mono)] text-xs text-muted-foreground">
                  halluciwatch-demo
                </span>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="mt-1 h-6 w-6 shrink-0 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary">
                    Q
                  </div>
                  <div className="rounded-xl rounded-tl-none bg-muted/50 px-4 py-3 text-sm">
                    What year was the Eiffel Tower completed?
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="mt-1 h-6 w-6 shrink-0 rounded-full bg-chart-2/20 flex items-center justify-center text-xs font-bold text-chart-2">
                    A
                  </div>
                  <div className="space-y-3">
                    <div className="rounded-xl rounded-tl-none bg-muted/50 px-4 py-3 text-sm">
                      The Eiffel Tower was completed in{" "}
                      <span className="font-semibold text-foreground">1889</span>{" "}
                      for the 1889 World&apos;s Fair in Paris.
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1">
                        <div className="mb-1 flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">
                            Hallucination Risk
                          </span>
                          <span className="risk-low font-semibold">12%</span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: "12%" }}
                            transition={{ duration: 1.5, delay: 2.5, ease: "easeOut" }}
                            className="h-full rounded-full bg-gradient-to-r from-green-500 to-emerald-400"
                          />
                        </div>
                      </div>
                      <Badge variant="secondary" className="border-green-500/20 bg-green-500/10 text-green-400">
                        Low Risk
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

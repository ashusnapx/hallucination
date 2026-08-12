"use client";

import { motion } from "motion/react";
import { Search, Cpu, BarChart3, Rocket } from "lucide-react";

const steps = [
  {
    number: "01",
    icon: Search,
    title: "Signal Capture",
    description:
      "During each forward pass, PyTorch hooks extract entropy, token probabilities, attention weights, and hidden-layer activations from every transformer block.",
    color: "text-violet-400",
    bgColor: "bg-violet-500/10",
    borderColor: "border-violet-500/20",
  },
  {
    number: "02",
    icon: Cpu,
    title: "Fingerprint Construction",
    description:
      "Extracted signals are aggregated into a fixed-length feature vector — the hallucination fingerprint. Per-layer statistics form a compact, architecture-agnostic representation.",
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/20",
  },
  {
    number: "03",
    icon: BarChart3,
    title: "Classifier Training",
    description:
      "An XGBoost classifier learns to distinguish hallucinated outputs from factual ones using fingerprint vectors from HaluEval (35K samples) and TruthfulQA.",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/20",
  },
  {
    number: "04",
    icon: Rocket,
    title: "Real-Time Scoring",
    description:
      "The trained classifier wraps your LLM pipeline, computing a 0–1 hallucination risk score in under 50ms — before the response is shown to the user.",
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/20",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="relative py-24 sm:py-32">
      {/* Subtle background accent */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/[0.02] to-transparent" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <span className="font-[family-name:var(--font-geist-mono)] text-sm font-semibold tracking-widest text-primary uppercase">
            How It Works
          </span>
          <h2 className="font-[family-name:var(--font-display)] mt-4 text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            Four-phase pipeline
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            From raw neural signals to actionable risk scores in a single
            inference pass.
          </p>
        </motion.div>

        <div className="relative mt-20">
          {/* Connection line */}
          <div className="absolute left-[39px] top-0 bottom-0 hidden w-px bg-gradient-to-b from-violet-500/50 via-blue-500/50 to-amber-500/50 lg:left-1/2 lg:-translate-x-px" />

          <div className="space-y-12 lg:space-y-24">
            {steps.map((step, index) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, x: index % 2 === 0 ? -40 : 40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{
                  duration: 0.7,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className={`relative flex flex-col items-center gap-8 lg:flex-row ${
                  index % 2 === 0 ? "lg:flex-row" : "lg:flex-row-reverse"
                }`}
              >
                {/* Content */}
                <div
                  className={`flex-1 ${
                    index % 2 === 0 ? "lg:text-right" : "lg:text-left"
                  }`}
                >
                  <div
                    className={`inline-flex items-center gap-2 rounded-full border ${step.borderColor} ${step.bgColor} px-3 py-1 text-xs font-semibold ${step.color} mb-4`}
                  >
                    Step {step.number}
                  </div>
                  <h3 className="font-[family-name:var(--font-display)] text-2xl font-bold sm:text-3xl">
                    {step.title}
                  </h3>
                  <p className="mt-4 max-w-md text-muted-foreground leading-relaxed lg:ml-auto">
                    {step.description}
                  </p>
                </div>

                {/* Center node */}
                <div className="relative z-10 flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl border bg-background shadow-lg">
                  <step.icon className={`h-8 w-8 ${step.color}`} />
                </div>

                {/* Spacer for layout */}
                <div className="hidden flex-1 lg:block" />
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

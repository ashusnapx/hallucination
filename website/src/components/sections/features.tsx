"use client";

import { motion } from "motion/react";
import {
  Brain,
  Zap,
  Shield,
  BarChart3,
  Plug,
  Globe,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const features = [
  {
    icon: Brain,
    title: "Neural Signal Extraction",
    description:
      "Captures entropy, attention weights, hidden states, and token probabilities from every transformer layer using PyTorch hooks.",
    gradient: "from-violet-500/20 to-purple-500/20",
    iconColor: "text-violet-400",
  },
  {
    icon: Zap,
    title: "<50ms Latency",
    description:
      "Lightweight XGBoost classifier adds negligible overhead. Real-time scoring during inference, not after.",
    gradient: "from-amber-500/20 to-orange-500/20",
    iconColor: "text-amber-400",
  },
  {
    icon: Shield,
    title: "Pre-Generation Risk",
    description:
      "Predicts hallucination risk before the response is displayed. Proactive mitigation, not reactive detection.",
    gradient: "from-emerald-500/20 to-teal-500/20",
    iconColor: "text-emerald-400",
  },
  {
    icon: BarChart3,
    title: "Fingerprint Vectors",
    description:
      "Fixed-length feature vectors from per-layer statistics, eigenvalue decomposition, and spectral attention features.",
    gradient: "from-blue-500/20 to-cyan-500/20",
    iconColor: "text-blue-400",
  },
  {
    icon: Plug,
    title: "Plug & Play",
    description:
      "Works with any HuggingFace-compatible LLM. One wrapper class, zero model modifications required.",
    gradient: "from-pink-500/20 to-rose-500/20",
    iconColor: "text-pink-400",
  },
  {
    icon: Globe,
    title: "Open Source",
    description:
      "pip install halluciwatch. Apache 2.0 licensed. Compatible with LangChain, HuggingFace Pipelines, and custom deployments.",
    gradient: "from-indigo-500/20 to-sky-500/20",
    iconColor: "text-indigo-400",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] as const },
  },
};

export function Features() {
  return (
    <section id="features" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <span className="font-[family-name:var(--font-geist-mono)] text-sm font-semibold tracking-widest text-primary uppercase">
            Features
          </span>
          <h2 className="font-[family-name:var(--font-display)] mt-4 text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            Everything you need to{" "}
            <span className="gradient-text">detect hallucinations</span>
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            A complete pipeline from signal extraction to real-time scoring.
            No external databases, no additional API calls.
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((feature) => (
            <motion.div key={feature.title} variants={itemVariants}>
              <Card className="group glass-card glow-border h-full rounded-2xl border-0 transition-all duration-300 hover:-translate-y-1">
                <CardHeader>
                  <div
                    className={`mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${feature.gradient}`}
                  >
                    <feature.icon
                      className={`h-6 w-6 ${feature.iconColor}`}
                    />
                  </div>
                  <CardTitle className="font-[family-name:var(--font-display)] text-xl">
                    {feature.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base leading-relaxed text-muted-foreground">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function CardContent({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={className}>{children}</div>;
}

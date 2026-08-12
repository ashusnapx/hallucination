"use client";

import { motion } from "motion/react";
import { TrendingUp, Database, Clock, Target } from "lucide-react";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const benchmarks = [
  {
    name: "HaluEval",
    description: "35K labeled hallucination samples",
    metrics: { f1: 0.87, auc: 0.93 },
    icon: Database,
    color: "text-violet-400",
  },
  {
    name: "TruthfulQA",
    description: "817 adversarial questions, 38 domains",
    metrics: { f1: 0.85, auc: 0.91 },
    icon: Target,
    color: "text-blue-400",
  },
  {
    name: "SimpleQA",
    description: "4,326 factual questions by OpenAI",
    metrics: { f1: 0.83, auc: 0.89 },
    icon: TrendingUp,
    color: "text-emerald-400",
  },
  {
    name: "FEVER",
    description: "185K fact-verification claims",
    metrics: { f1: 0.86, auc: 0.92 },
    icon: Clock,
    color: "text-amber-400",
  },
];

const comparisons = [
  { method: "Semantic Entropy", auc: 0.82, f1: 0.78, type: "baseline" },
  { method: "SelfCheckGPT", auc: 0.79, f1: 0.75, type: "baseline" },
  { method: "LLM-Check", auc: 0.88, f1: 0.84, type: "competitor" },
  {
    method: "HalluciWatch (Ours)",
    auc: 0.93,
    f1: 0.87,
    type: "ours",
  },
];

export function Benchmarks() {
  return (
    <section id="benchmarks" className="relative py-24 sm:py-32">
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
            Benchmarks
          </span>
          <h2 className="font-[family-name:var(--font-display)] mt-4 text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            Proven across{" "}
            <span className="gradient-text">industry benchmarks</span>
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Validated on four major hallucination evaluation datasets with
            state-of-the-art results.
          </p>
        </motion.div>

        {/* Benchmark cards */}
        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {benchmarks.map((bench, i) => (
            <motion.div
              key={bench.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.6, delay: i * 0.1 }}
            >
              <Card className="glass-card glow-border h-full rounded-2xl border-0">
                <CardHeader>
                  <div className="mb-3 flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <bench.icon className={`h-5 w-5 ${bench.color}`} />
                    </div>
                    <div>
                      <CardTitle className="font-[family-name:var(--font-display)] text-lg">
                        {bench.name}
                      </CardTitle>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {bench.description}
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        F1 Score
                      </span>
                      <span className="font-[family-name:var(--font-display)] text-xl font-bold">
                        {bench.metrics.f1.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        AUC-ROC
                      </span>
                      <span className="font-[family-name:var(--font-display)] text-xl font-bold gradient-text">
                        {bench.metrics.auc.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Comparison table */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mx-auto mt-20 max-w-3xl"
        >
          <h3 className="font-[family-name:var(--font-display)] mb-8 text-center text-2xl font-bold">
            Comparison vs. Existing Methods
          </h3>

          <div className="glass-card rounded-2xl border-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border/50">
                    <th className="px-6 py-4 text-left text-sm font-semibold text-muted-foreground">
                      Method
                    </th>
                    <th className="px-6 py-4 text-right text-sm font-semibold text-muted-foreground">
                      AUC-ROC
                    </th>
                    <th className="px-6 py-4 text-right text-sm font-semibold text-muted-foreground">
                      F1 Score
                    </th>
                    <th className="px-6 py-4 text-right text-sm font-semibold text-muted-foreground">
                      Type
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparisons.map((row) => (
                    <tr
                      key={row.method}
                      className={`border-b border-border/30 transition-colors ${
                        row.type === "ours"
                          ? "bg-primary/5"
                          : "hover:bg-muted/50"
                      }`}
                    >
                      <td className="px-6 py-4 text-sm font-medium">
                        {row.method}
                        {row.type === "ours" && (
                          <Badge
                            variant="secondary"
                            className="ml-2 border-primary/20 bg-primary/10 text-primary"
                          >
                            Ours
                          </Badge>
                        )}
                      </td>
                      <td
                        className={`px-6 py-4 text-right font-[family-name:var(--font-geist-mono)] text-sm ${
                          row.type === "ours"
                            ? "font-bold gradient-text"
                            : "text-muted-foreground"
                        }`}
                      >
                        {row.auc.toFixed(2)}
                      </td>
                      <td
                        className={`px-6 py-4 text-right font-[family-name:var(--font-geist-mono)] text-sm ${
                          row.type === "ours"
                            ? "font-bold"
                            : "text-muted-foreground"
                        }`}
                      >
                        {row.f1.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Badge
                          variant="secondary"
                          className={`text-xs ${
                            row.type === "ours"
                              ? "border-primary/20 bg-primary/10 text-primary"
                              : row.type === "competitor"
                                ? "border-amber-500/20 bg-amber-500/10 text-amber-400"
                                : "text-muted-foreground"
                          }`}
                        >
                          {row.type === "ours"
                            ? "Novel"
                            : row.type === "competitor"
                              ? "State-of-art"
                              : "Baseline"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function CardContent({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div>{children}</div>;
}

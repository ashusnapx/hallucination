"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { Copy, Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { GITHUB_URL, INSTALL_CMD } from "@/lib/constants";

const codeSnippets = [
  {
    label: "Quick Start",
    language: "python",
    code: `from halluciwatch import HalluciWatch

hw = HalluciWatch.from_pretrained("meta-llama/Llama-3.1-8B")

# Get response with hallucination risk score
response, risk_score = hw.score("What year was the Eiffel Tower completed?")
print(f"Response: {response}")
print(f"Hallucination Risk: {risk_score:.1%}")`,
  },
  {
    label: "LangChain",
    language: "python",
    code: `from halluciwatch import HalluciWatch

hw = HalluciWatch.from_pretrained("meta-llama/Llama-3.1-8B")

# Use as a LangChain LLM
llm = hw.as_langchain_llm(max_new_tokens=256)

# Get risk score with any LangChain chain
result = llm.invoke("Explain quantum computing")
print(f"Risk Score: {hw.last_risk_score:.1%}")`,
  },
  {
    label: "Streaming",
    language: "python",
    code: `from halluciwatch import HalluciWatch

hw = HalluciWatch.from_pretrained("mistralai/Mistral-7B-v0.1")

# Stream tokens with live risk scoring
for token, risk in hw.score_streaming("Tell me about AI safety"):
    print(token, end="", flush=True)
    print(f" [risk: {risk:.1%}]", end="")`,
  },
  {
    label: "Installation",
    language: "bash",
    code: `# Core package
pip install halluciwatch

# With PyTorch support
pip install halluciwatch[torch]

# With LangChain integration
pip install halluciwatch[langchain]

# Everything
pip install halluciwatch[all]`,
  },
];

export function CodeExample() {
  const [active, setActive] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const textToCopy = active === 3 ? INSTALL_CMD : codeSnippets[active].code;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="docs" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <span className="font-[family-name:var(--font-geist-mono)] text-sm font-semibold tracking-widest text-primary uppercase">
            Documentation
          </span>
          <h2 className="font-[family-name:var(--font-display)] mt-4 text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
            Start in <span className="gradient-text">three lines</span>
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Plug-and-play integration with HuggingFace, LangChain, and custom
            LLM deployments.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mx-auto mt-16 max-w-4xl"
        >
          {/* Tab selector */}
          <div className="mb-4 flex flex-wrap gap-2">
            {codeSnippets.map((snippet, i) => (
              <button
                key={snippet.label}
                onClick={() => setActive(i)}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition-all duration-200 ${
                  active === i
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {snippet.label}
              </button>
            ))}
          </div>

          {/* Code block */}
          <div className="gradient-border">
            <div className="glass-card rounded-2xl overflow-hidden">
              <div className="flex items-center justify-between border-b border-border/50 px-6 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex gap-1.5">
                    <div className="h-3 w-3 rounded-full bg-red-500" />
                    <div className="h-3 w-3 rounded-full bg-yellow-500" />
                    <div className="h-3 w-3 rounded-full bg-green-500" />
                  </div>
                  <Badge variant="secondary" className="font-[family-name:var(--font-geist-mono)] text-xs">
                    {codeSnippets[active].language}
                  </Badge>
                </div>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-green-400" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      Copy
                    </>
                  )}
                </button>
              </div>
              <pre className="overflow-x-auto p-6">
                <code className="font-[family-name:var(--font-geist-mono)] text-sm leading-relaxed">
                  {active === 3 ? INSTALL_CMD : codeSnippets[active].code}
                </code>
              </pre>
            </div>
          </div>

          {/* GitHub link below code */}
          <div className="mt-6 flex justify-center">
            <button
              onClick={() => window.open(GITHUB_URL, "_blank")}
              className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              View full documentation on GitHub
            </button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

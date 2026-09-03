import type { Metadata } from "next";
import { PageHeader } from "@/components/site/page-header";
import { NextPage } from "@/components/site/next-page";
import { Demo } from "@/components/sections/demo";

export const metadata: Metadata = {
  title: "Live demo",
  description:
    "Score a real answer from a local model. The answer and the risk come from the same forward pass — no second model grades the first.",
};

export default function Page() {
  return (
    <>
      <PageHeader
        eyebrow="Live"
        title={
          <>
            Watch it read a model&rsquo;s <em>own uncertainty</em>
          </>
        }
        lede="This runs against a real local model on this machine. The answer and the score come from the same forward pass — there is no second model grading the first."
        meta={[
          { label: "Model", value: "llama3.2:3b" },
          { label: "Runtime", value: "Ollama, local" },
          { label: "Needs", value: "make serve" },
        ]}
      />
      <Demo />
      <NextPage
        href="/results"
        eyebrow="Next"
        title="The numbers behind the score"
        blurb="AUROC, calibration error and the cost/quality frontier, with bootstrap intervals."
      />
    </>
  );
}

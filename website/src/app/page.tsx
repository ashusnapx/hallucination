import { Hero } from "@/components/sections/hero";
import { Explainer } from "@/components/sections/explainer";
import { Problem } from "@/components/sections/problem";
import { HowItWorks } from "@/components/sections/how-it-works";
import { Golden } from "@/components/sections/golden";
import { Checklist } from "@/components/sections/checklist";
import { Install } from "@/components/sections/install";
import { ClosingCta } from "@/components/sections/closing-cta";

export default function Home() {
  return (
    <>
      <Hero />
      <Explainer />
      <Problem />
      <HowItWorks />
      <Golden />
      <Checklist />
      <Install />
      <ClosingCta />
    </>
  );
}

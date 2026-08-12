import { Navbar } from "@/components/sections/navbar";
import { Hero } from "@/components/sections/hero";
import { Features } from "@/components/sections/features";
import { HowItWorks } from "@/components/sections/how-it-works";
import { LiveDemo } from "@/components/sections/live-demo";
import { Benchmarks } from "@/components/sections/benchmarks";
import { CodeExample } from "@/components/sections/code-example";
import { CTA } from "@/components/sections/cta";
import { Footer } from "@/components/sections/footer";

export default function Home() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        <Hero />
        <Features />
        <HowItWorks />
        <LiveDemo />
        <Benchmarks />
        <CodeExample />
        <CTA />
      </main>
      <Footer />
    </>
  );
}

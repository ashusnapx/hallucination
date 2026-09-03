import type { Metadata, Viewport } from "next";
import { Instrument_Serif, Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { Nav } from "@/components/site/nav";
import { Footer } from "@/components/site/footer";
import "./globals.css";

// next/font self-hosts and preloads, which removes the render-blocking request
// and the layout shift that @fontsource leaves behind.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-instrument-serif",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

const DESCRIPTION =
  "HalluciWatch scores how likely a local LLM's answer is a hallucination, from the model's own token probabilities. Runs entirely on your machine through Ollama — no API keys, no judge model.";

export const metadata: Metadata = {
  metadataBase: new URL("https://halluciwatch.dev"),
  title: {
    default: "HalluciWatch — hallucination risk scoring for local LLMs",
    template: "%s · HalluciWatch",
  },
  description: DESCRIPTION,
  keywords: [
    "hallucination detection",
    "LLM uncertainty",
    "semantic entropy",
    "Ollama",
    "local LLM",
    "AI safety",
    "calibration",
  ],
  authors: [{ name: "HalluciWatch" }],
  openGraph: {
    type: "website",
    title: "HalluciWatch — hallucination risk scoring for local LLMs",
    description: DESCRIPTION,
    siteName: "HalluciWatch",
  },
  twitter: {
    card: "summary_large_image",
    title: "HalluciWatch",
    description: DESCRIPTION,
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fbfaf7" },
    { media: "(prefers-color-scheme: dark)", color: "#232120" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${instrumentSerif.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        {/* Motion ships the entrance styles inline, so a scroll-reveal section
            is `opacity:0` in the server HTML and stays invisible if the bundle
            fails to load. The text is present for crawlers either way, but a
            human with broken JS would see blank panels — this makes the final
            state the fallback. */}
        <noscript>
          <style>{`[style*="opacity:0"]{opacity:1!important;transform:none!important}`}</style>
        </noscript>
      </head>
      <body className="antialiased">
        <ThemeProvider>
          <a
            href="#main"
            className="sr-only rounded-md px-4 py-2 focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-100 focus:bg-ink focus:text-paper"
          >
            Skip to content
          </a>
          <Nav />
          <main id="main">{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}

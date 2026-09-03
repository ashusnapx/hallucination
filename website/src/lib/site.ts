export const GITHUB_URL = "https://github.com/ashusnapx/halluciwatch";
export const PYPI_URL = "https://pypi.org/project/halluciwatch/";
export const PAPER_URL =
  "https://github.com/ashusnapx/halluciwatch/blob/main/backend/RESULTS.md";
export const INSTALL_CMD = "pip install halluciwatch";

/** Measured on llama3.2:3b over 520 TriviaQA + NQ-Open questions,
 *  5-fold CV grouped by question, 51.8% hallucination base rate.
 *  Source: backend/RESULTS.md — keep in sync. */
export const RESULTS = {
  auroc: 0.818,
  aurocCI: [0.778, 0.859] as const,
  auprc: 0.823,
  f1: 0.757,
  ece: 0.077,
  brier: 0.18,
  n: 448,
  baseRate: 0.509,
  model: "llama3.2:3b",
} as const;

/**
 * Academic attribution shown in the footer.
 *
 * The submitted synopsis and slide deck contain no student name, roll number,
 * guide name or institution — the only identifying line in either document is
 * "B.E. Computer Science & Engineering | 2025-26". These are placeholders
 * rather than invented details; fill them in before publishing.
 */
export const PROJECT_CREDITS = [
  { label: "Project", value: "Hallucination Fingerprinting in LLMs" },
  { label: "Programme", value: "B.E. Computer Science & Engineering" },
  { label: "Phase", value: "Phase 1 — Proposal & Literature Review" },
  { label: "Academic year", value: "2025–26" },
] as const;

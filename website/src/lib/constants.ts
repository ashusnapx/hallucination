"use client";

export function scrollTo(id: string) {
  const el = document.getElementById(id);
  if (el) {
    const offset = 80; // navbar height
    const y = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top: y, behavior: "smooth" });
  }
}

export const GITHUB_URL = "https://github.com/halluciwatch/halluciwatch";
export const PYPI_URL = "https://pypi.org/project/halluciwatch/";
export const DOCS_URL = "#docs";
export const INSTALL_CMD = "pip install halluciwatch";

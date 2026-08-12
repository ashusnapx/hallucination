"""Gemini API client — transparent, step-by-step hallucination scoring pipeline.

Every number this module produces is auditable: the pipeline records each
Gemini call, each extracted claim, each verdict, and the exact arithmetic that
turns those verdicts into a single risk score. It also emits a Mermaid
flowchart describing the run so the UI can render the real data flow.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

# Lite models only, ordered best → fallback. If one is rate limited (429) or
# unavailable (404) we transparently fall through to the next.
MODEL_CHAIN: list[str] = [
    os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
]

MAX_RETRIES = 3
BACKOFF_BASE_S = 1.5

# Risk weight per verdict. This is the whole scoring model — nothing hidden.
VERDICT_WEIGHTS: dict[str, float] = {
    "CORRECT": 0.0,
    "UNVERIFIABLE": 0.3,
    "INCORRECT": 0.8,
}

RISK_BANDS = [(0.3, "low"), (0.7, "medium"), (1.01, "high")]


class QuotaExhausted(RuntimeError):
    """Every model in the chain returned 429."""


@dataclass
class PipelineStep:
    """One step in the scoring pipeline."""

    step_number: int
    name: str
    description: str
    input_text: str
    output_text: str
    duration_ms: float
    status: str  # "ok" | "error"
    model_used: str = ""
    explanation: str = ""


@dataclass
class ClaimVerdict:
    """A single claim and how it was judged."""

    index: int
    claim: str
    verdict: str
    reason: str
    weight: float
    contribution: float


@dataclass
class Calculation:
    """Full audit trail of the risk arithmetic."""

    total_claims: int
    correct: int
    incorrect: int
    unverifiable: int
    weights: dict
    terms: list
    numerator: float
    denominator: int
    raw_score: float
    risk_score: float
    confidence: float
    formula: str
    substituted: str
    steps_human: list


@dataclass
class GeminiScore:
    """Full result from the scoring pipeline."""

    question: str
    response: str
    risk_score: float
    risk_label: str
    confidence: float
    factual_claims: list
    claim_verdicts: list
    claim_details: list
    verification_notes: str
    model_used: str
    total_latency_ms: float
    calculation: Optional[dict] = None
    mermaid: str = ""
    steps: list = field(default_factory=list)
    degraded: bool = False
    error: Optional[str] = None


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to backend/.env as GEMINI_API_KEY=..."
        )
    from google import genai

    return genai.Client(api_key=api_key)


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


def _is_unavailable(exc: Exception) -> bool:
    text = str(exc)
    return any(code in text for code in ("404", "NOT_FOUND", "503", "UNAVAILABLE"))


def _call_gemini(
    client, prompt: str, temperature: float = 0.3, json_mode: bool = False
) -> tuple[str, float, str]:
    """Single Gemini call with model fallback + backoff.

    Returns (text, latency_ms, model_actually_used).
    Raises QuotaExhausted only when every lite model is rate limited.
    """
    start = time.time()
    last_exc: Optional[Exception] = None
    saw_rate_limit = False

    for model in MODEL_CHAIN:
        for attempt in range(MAX_RETRIES):
            try:
                config: dict[str, Any] = {
                    "temperature": temperature,
                    "max_output_tokens": 4096,
                }
                if json_mode:
                    config["response_mime_type"] = "application/json"
                resp = client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                text = (resp.text or "").strip()
                if not text:
                    raise ValueError("Model returned an empty response")
                return text, (time.time() - start) * 1000, model
            except Exception as exc:  # noqa: BLE001 - classified below
                last_exc = exc
                if _is_rate_limit(exc):
                    saw_rate_limit = True
                    # Rate limited: back off once, then move to the next model.
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(BACKOFF_BASE_S * (2**attempt))
                        continue
                    break
                if _is_unavailable(exc):
                    break  # try the next model immediately
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BACKOFF_BASE_S * (2**attempt))
                    continue
                break

    if saw_rate_limit:
        raise QuotaExhausted(
            "All Gemini lite models are rate limited (429 RESOURCE_EXHAUSTED). "
            "Your API key has exhausted its free-tier quota — wait for the quota "
            "window to reset or enable billing."
        ) from last_exc
    raise RuntimeError(f"Gemini call failed: {last_exc}") from last_exc


def _extract_json(text: str) -> Any:
    """Parse JSON from a model response, tolerating fences and prose."""
    if not text:
        return None
    cleaned = text.strip()
    # Strip ```json ... ``` fences
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Fall back to the first balanced array/object in the text
    for opener, closer in (("[", "]"), ("{", "}")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def _normalize_claims(parsed: Any, fallback: str) -> list[str]:
    """Coerce whatever the model returned into a list of claim strings."""
    if isinstance(parsed, dict):
        for key in ("claims", "facts", "factual_claims", "items", "results"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break
    if isinstance(parsed, list):
        claims: list[str] = []
        for item in parsed:
            if isinstance(item, str) and item.strip():
                claims.append(item.strip())
            elif isinstance(item, dict):
                value = item.get("claim") or item.get("text") or item.get("statement")
                if isinstance(value, str) and value.strip():
                    claims.append(value.strip())
        if claims:
            return claims
    return [fallback.strip()] if fallback.strip() else []


def _normalize_verdicts(parsed: Any, claims: list[str]) -> list[dict]:
    """Coerce model output into [{claim, verdict, reason}] aligned to `claims`.

    This is the function that used to crash the server: Gemini sometimes returns
    a bare list of strings (["CORRECT", ...]) or an object wrapper instead of the
    requested list of objects.
    """
    if isinstance(parsed, dict):
        for key in ("verdicts", "results", "claims", "items", "evaluations"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break

    normalized: list[dict] = []
    if isinstance(parsed, list):
        for i, item in enumerate(parsed):
            claim = claims[i] if i < len(claims) else ""
            if isinstance(item, dict):
                verdict = str(
                    item.get("verdict") or item.get("label") or item.get("result") or ""
                ).strip().upper()
                normalized.append(
                    {
                        "claim": str(item.get("claim") or claim),
                        "verdict": verdict if verdict in VERDICT_WEIGHTS else "UNVERIFIABLE",
                        "reason": str(item.get("reason") or item.get("explanation") or ""),
                    }
                )
            elif isinstance(item, str):
                verdict = item.strip().upper()
                normalized.append(
                    {
                        "claim": claim,
                        "verdict": verdict if verdict in VERDICT_WEIGHTS else "UNVERIFIABLE",
                        "reason": "Model returned a bare verdict with no reasoning.",
                    }
                )

    # Pad so every claim gets a verdict.
    while len(normalized) < len(claims):
        normalized.append(
            {
                "claim": claims[len(normalized)],
                "verdict": "UNVERIFIABLE",
                "reason": "No verdict returned for this claim.",
            }
        )
    return normalized[: len(claims)] if claims else normalized


def _band(score: float) -> str:
    for threshold, label in RISK_BANDS:
        if score < threshold:
            return label
    return "high"


def _build_calculation(verdicts: list[dict]) -> tuple[Calculation, list[ClaimVerdict]]:
    """Turn verdicts into the risk score, recording every intermediate value."""
    details: list[ClaimVerdict] = []
    terms: list[dict] = []

    for i, v in enumerate(verdicts):
        verdict = v.get("verdict", "UNVERIFIABLE")
        weight = VERDICT_WEIGHTS.get(verdict, 0.3)
        details.append(
            ClaimVerdict(
                index=i + 1,
                claim=v.get("claim", ""),
                verdict=verdict,
                reason=v.get("reason", ""),
                weight=weight,
                contribution=weight,
            )
        )
        terms.append(
            {
                "index": i + 1,
                "claim": v.get("claim", ""),
                "verdict": verdict,
                "weight": weight,
            }
        )

    correct = sum(1 for v in details if v.verdict == "CORRECT")
    incorrect = sum(1 for v in details if v.verdict == "INCORRECT")
    unverifiable = sum(1 for v in details if v.verdict == "UNVERIFIABLE")
    denominator = max(1, len(details))

    numerator = incorrect * VERDICT_WEIGHTS["INCORRECT"] + unverifiable * VERDICT_WEIGHTS["UNVERIFIABLE"]
    raw = numerator / denominator
    risk = max(0.0, min(1.0, raw))
    confidence = (correct / denominator) * 100 if details else 0.0

    formula = "risk = ( n_incorrect x 0.8  +  n_unverifiable x 0.3 ) / n_total"
    substituted = (
        f"risk = ( {incorrect} x 0.8  +  {unverifiable} x 0.3 ) / {denominator}"
        f"  =  ( {incorrect * 0.8:.1f} + {unverifiable * 0.3:.1f} ) / {denominator}"
        f"  =  {numerator:.2f} / {denominator}  =  {risk:.4f}  =  {risk:.1%}"
    )

    steps_human = [
        f"1. The response was split into {len(details)} independently checkable factual claim(s).",
        f"2. Each claim was fact-checked and labelled CORRECT, INCORRECT or UNVERIFIABLE. "
        f"Result: {correct} correct, {incorrect} incorrect, {unverifiable} unverifiable.",
        "3. Each label carries a risk weight — CORRECT = 0.0 (no risk), "
        "UNVERIFIABLE = 0.3 (soft penalty, it might be invented), "
        "INCORRECT = 0.8 (hard penalty, it is provably wrong).",
        f"4. The weights are summed: {incorrect} x 0.8 + {unverifiable} x 0.3 = {numerator:.2f}.",
        f"5. The sum is divided by the claim count to get a per-claim average: "
        f"{numerator:.2f} / {denominator} = {risk:.4f}.",
        f"6. That value is clamped to [0, 1] and read as a percentage: {risk:.1%} risk, "
        f"which falls in the '{_band(risk)}' band "
        f"(low < 30% <= medium < 70% <= high).",
        f"7. Confidence is the share of claims that were positively verified: "
        f"{correct}/{denominator} = {confidence:.0f}%.",
    ]

    calc = Calculation(
        total_claims=len(details),
        correct=correct,
        incorrect=incorrect,
        unverifiable=unverifiable,
        weights=dict(VERDICT_WEIGHTS),
        terms=terms,
        numerator=round(numerator, 4),
        denominator=denominator,
        raw_score=round(raw, 6),
        risk_score=round(risk, 6),
        confidence=round(confidence, 2),
        formula=formula,
        substituted=substituted,
        steps_human=steps_human,
    )
    return calc, details


def _mermaid_escape(text: str, limit: int = 58) -> str:
    """Make arbitrary text safe inside a Mermaid node label."""
    clean = re.sub(r"\s+", " ", text or "").strip()
    clean = clean.replace('"', "'").replace("`", "'")
    clean = re.sub(r"[<>{}()\[\]|#;]", "", clean)
    if len(clean) > limit:
        clean = clean[: limit - 1].rstrip() + "…"
    return clean or "—"


def _build_mermaid(
    question: str,
    response: str,
    details: list[ClaimVerdict],
    calc: Calculation,
    risk_label: str,
    model_used: str,
) -> str:
    """Generate a Mermaid flowchart of this specific run, with real numbers."""
    lines = [
        "flowchart TD",
        f'    Q["🧑 Question<br/><small>{_mermaid_escape(question)}</small>"]',
        f'    G["⚡ Step 1 · Generate<br/><small>{_mermaid_escape(model_used)}</small>"]',
        f'    R["💬 Draft answer<br/><small>{_mermaid_escape(response, 70)}</small>"]',
        f'    E["🔍 Step 2 · Extract claims<br/><small>{calc.total_claims} claim(s) found</small>"]',
        "    Q --> G --> R --> E",
        "",
        "    subgraph VERIFY[\"🧪 Step 3 · Fact-check each claim independently\"]",
        "    direction TB",
    ]

    if details:
        for d in details:
            icon = {"CORRECT": "✅", "INCORRECT": "❌"}.get(d.verdict, "❓")
            lines.append(
                f'    C{d.index}["{icon} Claim {d.index}: {_mermaid_escape(d.claim, 46)}'
                f'<br/><small>{d.verdict} → weight {d.weight}</small>"]'
            )
    else:
        lines.append('    C0["❓ No claims extracted"]')
    lines.append("    end")
    lines.append("")

    for d in details:
        lines.append(f"    E --> C{d.index}")

    lines.extend(
        [
            "",
            f'    SUM["➕ Step 4a · Sum the weights<br/><small>{calc.incorrect} x 0.8 + '
            f'{calc.unverifiable} x 0.3 = {calc.numerator}</small>"]',
            f'    DIV["➗ Step 4b · Divide by claim count<br/><small>{calc.numerator} / '
            f'{calc.denominator} = {calc.risk_score:.4f}</small>"]',
            f'    OUT["🎯 Risk score<br/><b>{calc.risk_score:.1%}</b> · {risk_label.upper()}<br/>'
            f'<small>confidence {calc.confidence:.0f}%</small>"]',
        ]
    )

    if details:
        for d in details:
            lines.append(f"    C{d.index} --> SUM")
    else:
        lines.append("    C0 --> SUM")
    lines.append("    SUM --> DIV --> OUT")

    # Styling
    lines.extend(
        [
            "",
            "    classDef ok fill:#10281c,stroke:#34d399,stroke-width:1px,color:#a7f3d0;",
            "    classDef bad fill:#2c1116,stroke:#f87171,stroke-width:1px,color:#fecaca;",
            "    classDef unk fill:#2a2312,stroke:#fbbf24,stroke-width:1px,color:#fde68a;",
            "    classDef proc fill:#16182e,stroke:#818cf8,stroke-width:1px,color:#c7d2fe;",
            "    classDef result fill:#1b1340,stroke:#a78bfa,stroke-width:2px,color:#ede9fe;",
        ]
    )
    ok = [f"C{d.index}" for d in details if d.verdict == "CORRECT"]
    bad = [f"C{d.index}" for d in details if d.verdict == "INCORRECT"]
    unk = [f"C{d.index}" for d in details if d.verdict == "UNVERIFIABLE"]
    if ok:
        lines.append(f"    class {','.join(ok)} ok;")
    if bad:
        lines.append(f"    class {','.join(bad)} bad;")
    if unk:
        lines.append(f"    class {','.join(unk)} unk;")
    lines.append("    class Q,G,R,E,SUM,DIV proc;")
    lines.append("    class OUT result;")

    return "\n".join(lines)


def score_question(question: str, response: Optional[str] = None) -> GeminiScore:
    """Run the full pipeline and return every intermediate value."""
    question = (question or "").strip()
    if not question:
        raise ValueError("`question` must not be empty.")

    client = _get_client()
    steps: list[PipelineStep] = []
    total_start = time.time()
    model_used = MODEL_CHAIN[0]

    def finish_early(message: str) -> GeminiScore:
        """Bail out honestly instead of inventing a score."""
        return GeminiScore(
            question=question,
            response=response or "",
            risk_score=0.0,
            risk_label="unavailable",
            confidence=0.0,
            factual_claims=[],
            claim_verdicts=[],
            claim_details=[],
            verification_notes=message,
            model_used=model_used,
            total_latency_ms=(time.time() - total_start) * 1000,
            calculation=None,
            mermaid="",
            steps=[asdict(s) for s in steps],
            degraded=True,
            error=message,
        )

    # ── Step 1: Get a response to score ──────────────────────────────────────
    if response:
        steps.append(
            PipelineStep(
                step_number=1,
                name="Response Provided",
                description="Scoring the response you supplied — no generation needed.",
                input_text=question,
                output_text=response,
                duration_ms=0.0,
                status="ok",
                model_used="—",
                explanation=(
                    "You gave us both the question and the answer, so the pipeline skips "
                    "generation and goes straight to fact-checking."
                ),
            )
        )
    else:
        try:
            gen_prompt = (
                "Answer this question concisely in 1-3 sentences. "
                "Be specific and include concrete facts.\n\n"
                f"{question}"
            )
            response, gen_ms, model_used = _call_gemini(client, gen_prompt, temperature=0.3)
            steps.append(
                PipelineStep(
                    step_number=1,
                    name="Generate Response",
                    description=f"{model_used} answered the question.",
                    input_text=question,
                    output_text=response,
                    duration_ms=gen_ms,
                    status="ok",
                    model_used=model_used,
                    explanation=(
                        "First we need something to audit. The model answers the question "
                        "normally — exactly as it would in your own app — so we can then "
                        "check that answer for invented facts."
                    ),
                )
            )
        except QuotaExhausted as exc:
            steps.append(
                PipelineStep(
                    step_number=1,
                    name="Generate Response",
                    description="Rate limited by the Gemini API.",
                    input_text=question,
                    output_text=str(exc),
                    duration_ms=0.0,
                    status="error",
                    explanation="Every lite model returned 429, so no answer could be produced.",
                )
            )
            return finish_early(str(exc))
        except Exception as exc:  # noqa: BLE001
            steps.append(
                PipelineStep(
                    step_number=1,
                    name="Generate Response",
                    description="Generation failed.",
                    input_text=question,
                    output_text=str(exc),
                    duration_ms=0.0,
                    status="error",
                    explanation="The model could not produce an answer, so there is nothing to score.",
                )
            )
            return finish_early(f"Generation failed: {exc}")

    # ── Step 2: Extract atomic factual claims ────────────────────────────────
    claims_prompt = (
        "Break the text below into atomic, independently checkable factual claims.\n"
        "Return ONLY a JSON array of strings, e.g. [\"claim 1\", \"claim 2\"].\n"
        "Ignore opinions, hedging and filler. If there are no factual claims, return [].\n\n"
        f"TEXT: {response}"
    )
    try:
        claims_text, claims_ms, model_used = _call_gemini(
            client, claims_prompt, temperature=0.1, json_mode=True
        )
        claims = _normalize_claims(_extract_json(claims_text), response)
        steps.append(
            PipelineStep(
                step_number=2,
                name="Extract Claims",
                description=f"Split the answer into {len(claims)} checkable claim(s).",
                input_text=response,
                output_text=json.dumps(claims, indent=2),
                duration_ms=claims_ms,
                status="ok",
                model_used=model_used,
                explanation=(
                    "A paragraph is never wholly true or wholly false — usually one sentence "
                    "is invented while the rest is fine. Splitting the answer into atomic "
                    f"claims lets each one be judged on its own, so the final score reflects "
                    f"how much of the answer is unsafe, not just whether anything was wrong. "
                    f"Here it produced {len(claims)} claim(s)."
                ),
            )
        )
    except QuotaExhausted as exc:
        steps.append(
            PipelineStep(
                step_number=2,
                name="Extract Claims",
                description="Rate limited by the Gemini API.",
                input_text=response,
                output_text=str(exc),
                duration_ms=0.0,
                status="error",
                explanation="Claims could not be extracted, so no score can be computed.",
            )
        )
        return finish_early(str(exc))
    except Exception as exc:  # noqa: BLE001
        claims = [response]
        steps.append(
            PipelineStep(
                step_number=2,
                name="Extract Claims",
                description="Extraction failed — treating the whole answer as one claim.",
                input_text=response,
                output_text=str(exc),
                duration_ms=0.0,
                status="error",
                model_used=model_used,
                explanation="Falling back to scoring the response as a single claim.",
            )
        )

    if not claims:
        steps.append(
            PipelineStep(
                step_number=3,
                name="Verify Claims",
                description="No factual claims to verify.",
                input_text=response,
                output_text="[]",
                duration_ms=0.0,
                status="ok",
                model_used=model_used,
                explanation=(
                    "The answer contained no checkable factual assertions, so there is "
                    "nothing that can be hallucinated. Risk is 0%."
                ),
            )
        )

    # ── Step 3: Fact-check each claim ────────────────────────────────────────
    claims_block = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
    verdicts: list[dict] = []
    if claims:
        verify_prompt = (
            "You are a strict fact-checker. For EACH numbered claim below decide:\n"
            "  CORRECT      - you are confident it is true\n"
            "  INCORRECT    - you are confident it is false or fabricated\n"
            "  UNVERIFIABLE - it refers to something you cannot confirm exists\n\n"
            "Treat confidently-stated specifics you cannot confirm (case citations, "
            "study titles, statistics, dated events) as INCORRECT or UNVERIFIABLE — "
            "never as CORRECT.\n\n"
            f"CLAIMS:\n{claims_block}\n\n"
            "Return ONLY a JSON array with one object per claim, in the same order, "
            'each with keys "claim", "verdict" and "reason". '
            'Example: [{"claim":"...","verdict":"CORRECT","reason":"..."}]'
        )
        try:
            verify_text, verify_ms, model_used = _call_gemini(
                client, verify_prompt, temperature=0.1, json_mode=True
            )
            verdicts = _normalize_verdicts(_extract_json(verify_text), claims)
            counts = {
                k: sum(1 for v in verdicts if v["verdict"] == k) for k in VERDICT_WEIGHTS
            }
            steps.append(
                PipelineStep(
                    step_number=3,
                    name="Verify Claims",
                    description=(
                        f"{counts['CORRECT']} correct · {counts['INCORRECT']} incorrect · "
                        f"{counts['UNVERIFIABLE']} unverifiable"
                    ),
                    input_text=claims_block,
                    output_text=json.dumps(verdicts, indent=2),
                    duration_ms=verify_ms,
                    status="ok",
                    model_used=model_used,
                    explanation=(
                        "Each claim is checked on its own against the model's knowledge. "
                        "Confidently-stated specifics that cannot be confirmed — fake case "
                        "citations, invented studies, made-up statistics — are the signature "
                        "of a hallucination, so they are labelled INCORRECT or UNVERIFIABLE "
                        "rather than given the benefit of the doubt."
                    ),
                )
            )
        except QuotaExhausted as exc:
            steps.append(
                PipelineStep(
                    step_number=3,
                    name="Verify Claims",
                    description="Rate limited by the Gemini API.",
                    input_text=claims_block,
                    output_text=str(exc),
                    duration_ms=0.0,
                    status="error",
                    explanation="Without verdicts there is no basis for a score.",
                )
            )
            return finish_early(str(exc))
        except Exception as exc:  # noqa: BLE001
            steps.append(
                PipelineStep(
                    step_number=3,
                    name="Verify Claims",
                    description="Verification failed.",
                    input_text=claims_block,
                    output_text=str(exc),
                    duration_ms=0.0,
                    status="error",
                    explanation="Without verdicts there is no basis for a score.",
                )
            )
            return finish_early(f"Verification failed: {exc}")

    # ── Step 4: Compute the risk score ───────────────────────────────────────
    calc, details = _build_calculation(verdicts)
    risk_label = _band(calc.risk_score)

    steps.append(
        PipelineStep(
            step_number=4,
            name="Compute Risk Score",
            description=f"Risk = {calc.risk_score:.1%} ({risk_label})",
            input_text=json.dumps(verdicts, indent=2),
            output_text=f"{calc.formula}\n{calc.substituted}",
            duration_ms=0.0,
            status="ok",
            model_used="deterministic",
            explanation=(
                "This step is pure arithmetic — no model involved, so it is fully "
                "reproducible. Weighted verdicts are averaged over the claim count, which "
                "keeps the score comparable between a one-sentence answer and a long one."
            ),
        )
    )

    mermaid = _build_mermaid(
        question=question,
        response=response,
        details=details,
        calc=calc,
        risk_label=risk_label,
        model_used=model_used,
    )

    notes = [f"Claim {d.index} — {d.verdict}: {d.reason}" for d in details if d.reason]

    return GeminiScore(
        question=question,
        response=response,
        risk_score=calc.risk_score,
        risk_label=risk_label,
        confidence=calc.confidence,
        factual_claims=[d.claim for d in details],
        claim_verdicts=[d.verdict for d in details],
        claim_details=[asdict(d) for d in details],
        verification_notes=" ".join(notes) if notes else "No verification details returned.",
        model_used=model_used,
        total_latency_ms=(time.time() - total_start) * 1000,
        calculation=asdict(calc),
        mermaid=mermaid,
        steps=[asdict(s) for s in steps],
        degraded=any(s.status == "error" for s in steps),
        error=None,
    )

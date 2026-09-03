import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// The cascade can escalate to K extra generations on a local model, so a slow
// laptop needs real headroom here.
const TIMEOUT_MS = 120_000;

export async function POST(request: NextRequest) {
  let body: { question?: string; answer?: string; samples?: number };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const question = (body.question || "").trim();
  if (!question) {
    return NextResponse.json(
      { error: "A question is required." },
      { status: 400 },
    );
  }
  if (question.length > 4000) {
    return NextResponse.json(
      { error: "Question is too long (max 4000 chars)." },
      { status: 400 },
    );
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const upstream = await fetch(`${BACKEND_URL}/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        ...(body.answer ? { answer: body.answer } : {}),
        ...(typeof body.samples === "number" ? { samples: body.samples } : {}),
      }),
      signal: controller.signal,
    });

    const text = await upstream.text();

    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        {
          error: `Backend returned a non-JSON response (HTTP ${upstream.status}): ${text.slice(0, 300)}`,
        },
        { status: 502 },
      );
    }

    return NextResponse.json(data, {
      status: upstream.ok ? 200 : upstream.status,
    });
  } catch (error) {
    const aborted = error instanceof Error && error.name === "AbortError";
    return NextResponse.json(
      {
        error: aborted
          ? `Scoring did not finish within ${TIMEOUT_MS / 1000}s. A local model on a laptop can be slow when the cascade escalates to extra samples.`
          : `Cannot reach the scoring backend at ${BACKEND_URL}. Start it with:  cd backend && make serve  (and make sure 'ollama serve' is running).`,
      },
      { status: aborted ? 504 : 503 },
    );
  } finally {
    clearTimeout(timeout);
  }
}

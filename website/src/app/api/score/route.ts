import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const TIMEOUT_MS = 90_000;

export async function POST(request: NextRequest) {
  let body: { question?: string; response?: string };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const question = (body.question || "").trim();
  if (!question) {
    return NextResponse.json({ error: "A question is required." }, { status: 400 });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const upstream = await fetch(`${BACKEND_URL}/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        ...(body.response ? { response: body.response } : {}),
      }),
      signal: controller.signal,
    });

    const text = await upstream.text();

    // The backend answers with structured JSON even for failures — pass it
    // through untouched so the UI can explain exactly what went wrong.
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

    return NextResponse.json(data, { status: upstream.ok ? 200 : upstream.status });
  } catch (error) {
    const aborted = error instanceof Error && error.name === "AbortError";
    return NextResponse.json(
      {
        error: aborted
          ? `The backend did not respond within ${TIMEOUT_MS / 1000}s. It may be rate limited or still starting up.`
          : `Cannot reach the scoring backend at ${BACKEND_URL}. Start it with: cd backend && ./.venv/bin/python run_server.py`,
      },
      { status: aborted ? 504 : 503 },
    );
  } finally {
    clearTimeout(timeout);
  }
}

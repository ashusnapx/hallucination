"""Run the HalluciWatch API server."""
import os
import sys
from pathlib import Path

# Load .env from backend directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import uvicorn

if __name__ == "__main__":
    from halluciwatch.api.server import create_app
    app = create_app()
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting HalluciWatch API on port {port}")
    print(f"Gemini API configured: {bool(os.environ.get('GEMINI_API_KEY'))}")
    uvicorn.run(app, host="0.0.0.0", port=port)

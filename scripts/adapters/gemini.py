"""
Google Gemini adapter for ReviewSentry.

Calls the Gemini generateContent API via the REST endpoint.
Model examples: gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash

Setup: see docs/setup-gemini.md
"""

import json
import urllib.request

_BASE_URL = "https://generativelanguage.googleapis.com"


def call_api(
    api_key: str,
    model: str,
    system: str,
    user: str,
    base_url: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Call the Gemini generateContent API and return the review text."""
    root = base_url or _BASE_URL
    url  = f"{root}/v1beta/models/{model}:generateContent"

    payload = {
        "system_instruction": {
            "parts": [{"text": system}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user}]}
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "X-goog-api-key": api_key,
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError(f"Unexpected Gemini response structure: {data}")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError(f"Gemini response has no parts: {data}")

    return parts[0]["text"]

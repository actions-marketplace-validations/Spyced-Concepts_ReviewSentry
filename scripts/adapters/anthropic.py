"""
Anthropic adapter for ReviewSentry.

Calls the Anthropic Messages API with prompt caching enabled.
Model examples: claude-sonnet-4-6, claude-opus-4-7, claude-haiku-4-5-20251001

Setup: see docs/setup-anthropic.md
"""

import json
import urllib.request


def call_api(
    api_key: str,
    model: str,
    system: str,
    user: str,
    base_url: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Call the Anthropic Messages API and return the review text."""
    url = (base_url or "https://api.anthropic.com") + "/v1/messages"

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": user}],
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
            "content-type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    content = data.get("content", [])
    if not content or content[0].get("type") != "text":
        raise ValueError(f"Unexpected Anthropic response structure: {data}")

    return content[0]["text"]

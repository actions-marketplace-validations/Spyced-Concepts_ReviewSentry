"""
GitHub Models adapter for ReviewSentry.

Uses your existing GITHUB_TOKEN — no additional account or API key required.
Free within GitHub's rate limits.

Calls the GitHub Models inference endpoint (Azure AI Inference REST API).
Note: this endpoint uses /chat/completions, not /v1/chat/completions.

Model examples: gpt-4o, gpt-4o-mini, Meta-Llama-3.1-70B-Instruct, Mistral-large

Setup: see docs/setup-github-models.md
"""

import json
import urllib.request

_DEFAULT_BASE_URL = "https://models.inference.ai.azure.com"


def call_api(
    api_key: str,
    model: str,
    system: str,
    user: str,
    base_url: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Call the GitHub Models inference API and return the review text."""
    url = (base_url or _DEFAULT_BASE_URL) + "/chat/completions"

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    choices = data.get("choices", [])
    if not choices:
        raise ValueError(f"Unexpected GitHub Models response structure: {data}")

    return choices[0]["message"]["content"]

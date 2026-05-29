"""
OpenAI adapter for ReviewSentry.

Calls the OpenAI Chat Completions API. Also works with any OpenAI-compatible
endpoint — set AI_BASE_URL to use Groq, Azure OpenAI, Mistral, Ollama, or
any other provider that implements the OpenAI API spec.

Model examples: gpt-4o, gpt-4o-mini, gpt-4-turbo, o1-mini
For Groq: llama-3.3-70b-versatile, mixtral-8x7b-32768
For Ollama: llama3.2, qwen2.5-coder

Setup: see docs/setup-openai.md
"""

import json
import urllib.request

_DEFAULT_BASE_URL = "https://api.openai.com"


def call_api(
    api_key: str,
    model: str,
    system: str,
    user: str,
    base_url: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Call the OpenAI Chat Completions API and return the review text."""
    url = (base_url or _DEFAULT_BASE_URL) + "/v1/chat/completions"

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
        raise ValueError(f"Unexpected OpenAI response structure: {data}")

    return choices[0]["message"]["content"]

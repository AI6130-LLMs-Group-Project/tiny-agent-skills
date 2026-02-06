"""
Local LLM client: calls an OpenAI-compatible /v1/chat/completions endpoint (e.g. llama-server on port 1025).
Uses urllib only; no extra dependencies.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def chat(
    messages: list[dict[str, str]],
    *,
    base_url: str = "http://localhost:1025/v1",
    model: str = "qwen",
    max_tokens: int = 256,
) -> str:
    """
    Call local OpenAI-compatible chat completions; return assistant content text.

    Input:
      messages — list of {"role": "system"|"user"|"assistant", "content": "..."}.
      base_url — e.g. http://localhost:1025/v1 (default matches run_qwen3vl_server.sh --port 1025).
      model   — model name (often ignored by local server).
      max_tokens — max reply length.

    Output:
      str — stripped assistant reply text.

    Raises:
      RuntimeError — if request fails (e.g. server not running) or response has no choices.
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Local LLM call failed (ensure bash script/run_qwen3vl_server.sh is running): {e}"
        ) from e
    choice = (data.get("choices") or [None])[0]
    if not choice:
        raise RuntimeError(f"Local LLM returned no choices: {data}")
    content = (choice.get("message") or {}).get("content") or ""
    return content.strip()

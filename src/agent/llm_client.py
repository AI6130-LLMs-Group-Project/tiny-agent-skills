"""
调用本地 LLM 接口（如 script/run_qwen3vl_server.sh 起的 llama-server，port 1025）。
兼容 OpenAI 的 /v1/chat/completions，用 urllib 不额外依赖。
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
    调本地 OpenAI 兼容接口，发 chat completions 请求，返回 assistant 的 content 文本。
    base_url 默认对应 run_qwen3vl_server.sh 的 --port 1025。
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
            f"调用本地 LLM 失败（请先运行 bash script/run_qwen3vl_server.sh）: {e}"
        ) from e
    choice = (data.get("choices") or [None])[0]
    if not choice:
        raise RuntimeError(f"本地 LLM 返回无 choices: {data}")
    content = (choice.get("message") or {}).get("content") or ""
    return content.strip()

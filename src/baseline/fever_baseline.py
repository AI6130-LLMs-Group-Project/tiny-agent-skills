"""
FEVER baseline using prompt + one function-calling tool cycle.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from search import search_wiki


def load_dotenv() -> None:
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def apply_port_override(endpoint: str, port: int | None) -> str:
    base = endpoint.strip()
    if "://" not in base:
        base = "http://" + base
    if port is None:
        return base.rstrip("/")

    parsed = urllib.parse.urlsplit(base)
    host = parsed.hostname or "127.0.0.1"
    netloc = f"{host}:{port}"
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        netloc = f"{auth}@{netloc}"

    updated = urllib.parse.urlunsplit((parsed.scheme or "http", netloc, parsed.path, "", ""))
    return updated.rstrip("/")


def chat_completions_url(endpoint: str) -> str:
    base = endpoint.rstrip("/")
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def http_chat(base_endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = chat_completions_url(base_endpoint)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_tool_args(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        out = json.loads(raw)
        return out if isinstance(out, dict) else {}
    except json.JSONDecodeError:
        return {}


def parse_label(text: str) -> str:
    match = re.search(r"\b(SUPPORTS|REFUTES|NOT ENOUGH INFO)\b", (text or "").upper())
    if match:
        return match.group(1)
    return "NOT ENOUGH INFO"


def run_single_claim(
    claim: str,
    base_endpoint: str,
    model: str,
    temperature: float = 0.0,
) -> tuple[str, str]:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "wiki_search",
                "description": "Search Wikipedia for evidence related to a FEVER claim.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
                    },
                    "required": ["query"],
                },
            },
        }
    ]

    system = (
        "You are a FEVER fact-checking assistant.\n"
        "Use wiki_search when needed to gather evidence.\n"
        "After receiving tool output, respond with:\n"
        "Label: SUPPORTS|REFUTES|NOT ENOUGH INFO\n"
        "Reason: <short reason>"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Claim: {claim}"},
    ]

    first_payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "tools": tools,
        "tool_choice": "auto",
    }
    first_resp = http_chat(base_endpoint, first_payload)
    first_msg = (first_resp.get("choices") or [{}])[0].get("message", {}) or {}
    tool_calls = first_msg.get("tool_calls") or []

    if not tool_calls:
        text = first_msg.get("content", "") or ""
        return parse_label(text), text.strip()

    assistant_with_calls: dict[str, Any] = {
        "role": "assistant",
        "content": first_msg.get("content", "") or "",
        "tool_calls": tool_calls,
    }
    messages.append(assistant_with_calls)

    for call in tool_calls:
        fn = call.get("function", {}) or {}
        if fn.get("name") != "wiki_search":
            result = {"ok": False, "error": f"Unknown tool: {fn.get('name')}", "results": []}
        else:
            args = parse_tool_args(fn.get("arguments", ""))
            query = str(args.get("query", "")).strip()
            try:
                limit = int(args.get("limit", 3))
            except (TypeError, ValueError):
                limit = 3
            result = {"ok": True, "results": search_wiki(query, limit)}

        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": fn.get("name", ""),
                "content": json.dumps(result, ensure_ascii=True),
            }
        )

    second_payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    second_resp = http_chat(base_endpoint, second_payload)
    second_msg = (second_resp.get("choices") or [{}])[0].get("message", {}) or {}
    text = second_msg.get("content", "") or ""
    return parse_label(text), text.strip()


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Prompt + tool-calling FEVER baseline")
    parser.add_argument("--data", default="data/paper_dev.jsonl", help="FEVER jsonl path")
    parser.add_argument("--limit", type=int, default=1, help="Maximum random samples per run")
    parser.add_argument("--port", type=int, default=None, help="Override port from LLM_ENDPOINT")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed")
    parser.add_argument("--model", default="local-model", help="Model field sent to chat/completions")
    args = parser.parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be >= 1")

    load_dotenv()
    endpoint = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:1025")
    endpoint = apply_port_override(endpoint, args.port)

    data_path = Path(args.data)
    if not data_path.is_file():
        raise SystemExit(f"Dataset not found: {data_path}")
    rows = iter_jsonl(data_path)
    if not rows:
        raise SystemExit("Dataset is empty.")

    rng = random.Random(args.seed)
    sample_size = min(args.limit, len(rows))
    chosen = rng.sample(rows, k=sample_size)

    total = 0
    correct = 0
    print(f"Using LLM endpoint: {endpoint}")
    print(f"Evaluating random samples: {sample_size}")
    print("=" * 80)

    for row in chosen:
        claim = str(row.get("claim", "")).strip()
        gold = str(row.get("label", "NOT ENOUGH INFO")).upper()
        pred, raw = run_single_claim(claim=claim, base_endpoint=endpoint, model=args.model)

        total += 1
        hit = pred == gold
        if hit:
            correct += 1
        acc = correct / total

        print(f"[{total}] id={row.get('id')} | claim={claim}")
        print(f"  pred={pred} | gold={gold} | correct={hit} | acc={acc:.4f}")
        if raw:
            print(f"  model_output={raw}")
        print("-" * 80)

    print(f"Done. evaluated={total}, correct={correct}, accuracy={correct / max(total, 1):.4f}")


if __name__ == "__main__":
    main()

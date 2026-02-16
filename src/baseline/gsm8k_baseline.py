"""
Single-pass GSM8K baseline with prompt + function-calling math utilities.
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

from mathutils import TOOL_DEFINITIONS, call_tool, parse_tool_args


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
    return urllib.parse.urlunsplit((parsed.scheme or "http", netloc, parsed.path, "", "")).rstrip("/")


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


def parse_number(text: str) -> float | None:
    if not text:
        return None

    line_match = re.search(r"final\s*answer\s*:\s*(.+)", text, flags=re.IGNORECASE)
    target = line_match.group(1) if line_match else text

    tokens = re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?(?:\s*/\s*\d+)?", target)
    if not tokens:
        return None
    token = tokens[-1].replace(",", "").strip()

    if "/" in token:
        left, right = token.split("/", 1)
        try:
            denom = float(right.strip())
            if denom == 0:
                return None
            return float(left.strip()) / denom
        except ValueError:
            return None
    try:
        return float(token)
    except ValueError:
        return None


def parse_gold_answer(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return parse_number(value)
    return None


def solve_question(
    question: str,
    base_endpoint: str,
    model: str,
    temperature: float,
    max_tool_calls: int,
) -> str:
    system = (
        "You are solving GSM8K math word problems.\n"
        "Use the provided math tools whenever calculations are needed.\n"
        "When done, output exactly one line in this format:\n"
        "Final Answer: <number>\n"
        "Do not include units or extra text in the final line."
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Question: {question}"},
    ]

    for _ in range(max_tool_calls + 1):
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
        }
        resp = http_chat(base_endpoint, payload)
        msg = (resp.get("choices") or [{}])[0].get("message", {}) or {}
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            return content.strip()

        messages.append(
            {
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
            }
        )
        for call in tool_calls:
            fn = call.get("function", {}) or {}
            name = fn.get("name", "")
            args = parse_tool_args(fn.get("arguments", ""))
            out = call_tool(name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "name": name,
                    "content": json.dumps(out, ensure_ascii=True),
                }
            )

    messages.append(
        {
            "role": "user",
            "content": "Now return the result in one line only: Final Answer: <number>",
        }
    )
    final_resp = http_chat(
        base_endpoint,
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        },
    )
    final_msg = (final_resp.get("choices") or [{}])[0].get("message", {}) or {}
    return (final_msg.get("content", "") or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Prompt + function-calling baseline for GSM8K")
    parser.add_argument("--data", default="data/ps/gsm8k/gsm8k.json", help="Path to GSM8K json file")
    parser.add_argument("--limit", type=int, default=20, help="Maximum random samples per run")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed")
    parser.add_argument("--model", default="local-model", help="Model field sent to chat/completions")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--max-tool-calls", type=int, default=3, help="Max tool-calling rounds per sample")
    parser.add_argument("--tol", type=float, default=1e-6, help="Absolute tolerance for numeric match")
    parser.add_argument("--port", type=int, default=None, help="Override port from LLM_ENDPOINT")
    args = parser.parse_args()

    if args.limit < 1:
        raise SystemExit("--limit must be >= 1")
    if args.max_tool_calls < 0:
        raise SystemExit("--max-tool-calls must be >= 0")

    load_dotenv()
    endpoint = apply_port_override(os.getenv("LLM_ENDPOINT", "http://127.0.0.1:1025"), args.port)

    data_path = Path(args.data)
    if not data_path.is_file():
        raise SystemExit(f"Dataset not found: {data_path}")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise SystemExit("Dataset must be a non-empty JSON list.")

    rng = random.Random(args.seed)
    sample_size = min(args.limit, len(data))
    rows = rng.sample(data, k=sample_size)

    total = 0
    correct = 0
    print(f"Using LLM endpoint: {endpoint}")
    print(f"Evaluating random samples: {sample_size}")
    print("=" * 80)

    for row in rows:
        question = str(row.get("question", "")).strip()
        gold = parse_gold_answer(row.get("answer"))

        pred = None
        raw_output = ""
        error = ""
        try:
            raw_output = solve_question(
                question=question,
                base_endpoint=endpoint,
                model=args.model,
                temperature=args.temperature,
                max_tool_calls=args.max_tool_calls,
            )
            pred = parse_number(raw_output)
        except Exception as exc:
            error = str(exc)

        total += 1
        hit = bool(pred is not None and gold is not None and abs(pred - gold) <= args.tol)
        if hit:
            correct += 1
        acc = correct / total

        print(f"[{total}] question={question}")
        print(f"  pred={pred} | gold={gold} | correct={hit} | acc={acc:.4f}")
        if raw_output:
            print(f"  model_output={raw_output}")
        if error:
            print(f"  error={error}")
        print("-" * 80)

    print(f"Done. evaluated={total}, correct={correct}, accuracy={correct / max(total, 1):.4f}")


if __name__ == "__main__":
    main()

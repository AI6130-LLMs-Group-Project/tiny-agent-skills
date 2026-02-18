from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Callable, Dict, List, Tuple

from orchestrator import Orchestrator
from state import AgentState


DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "ps" / "gsm8k" / "gsm8k.json"


def _read_rows(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    raise ValueError("GSM dataset must be a JSON list of objects.")


def _pick_rows(rows: List[Dict], start: int, limit: int, random_mode: bool, seed: int) -> List[Dict]:
    sliced = rows[start:] if start > 0 else list(rows)
    if random_mode:
        rng = random.Random(seed)
        rng.shuffle(sliced)
    return sliced[:limit]


def _coerce_float(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _predict_answer(question: str, step_callback: Callable[[Dict], None] | None = None) -> Tuple[float | None, AgentState]:
    state = AgentState(sid="gsm8k", task="gsm8k", fsm="PARSE_PROBLEM")
    orch = Orchestrator(state)
    try:
        orch.run(question, step_callback=step_callback)
    except Exception:
        return None, state

    output = state.output or {}
    rows = output.get("out") if isinstance(output, dict) else None
    if isinstance(rows, list) and rows:
        row0 = rows[0] if isinstance(rows[0], dict) else {}
        return _coerce_float(row0.get("answer")), state
    return None, state


def _is_correct(pred: float | None, gold: float | None, tol: float) -> bool:
    if pred is None or gold is None:
        return False
    return abs(pred - gold) <= tol


def _print_step(event: Dict) -> None:
    step = event.get("step")
    state = event.get("state")
    status = event.get("status")
    explanation = event.get("explanation", "")
    next_steps = event.get("next_steps", "")
    detail = event.get("detail", {})

    print(f"  [step {step}] {state} -> {status}", flush=True)
    print(f"    explanation: {explanation}", flush=True)
    print(f"    next: {next_steps}", flush=True)
    if detail:
        print(f"    detail: {json.dumps(detail, ensure_ascii=True)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run soft-FSM math solving on GSM8K JSON.")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="Path to GSM8K JSON file.")
    parser.add_argument("--limit", type=int, default=20, help="Max rows to evaluate.")
    parser.add_argument("--start", type=int, default=0, help="Start row offset.")
    parser.add_argument("--random", action="store_true", help="Sample records randomly instead of sequential order.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used when --random is enabled.")
    parser.add_argument("--tol", type=float, default=1e-6, help="Numeric tolerance for answer matching.")
    parser.add_argument("--show-trace", action="store_true", help="Print action history for each sample.")
    parser.add_argument(
        "--live-steps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Stream explanation/next-step logs in real time for each FSM stage.",
    )
    args = parser.parse_args()

    path = Path(args.data)
    if not path.is_file():
        raise SystemExit(f"Dataset not found: {path}")

    rows = _read_rows(path)
    selected = _pick_rows(rows, start=args.start, limit=args.limit, random_mode=args.random, seed=args.seed)

    total = 0
    correct = 0
    for idx, row in enumerate(selected, start=1):
        qid = row.get("id", idx)
        question = str(row.get("question", ""))
        gold = _coerce_float(row.get("answer"))
        print(f"[{idx}] id={qid} | question={question}", flush=True)

        callback = _print_step if args.live_steps else None
        pred, state = _predict_answer(question, step_callback=callback)

        total += 1
        hit = _is_correct(pred, gold, args.tol)
        if hit:
            correct += 1
        acc = correct / total

        print(
            f"  model_answer={pred} | gold={gold} | correct={hit} | cumulative_acc={acc:.4f}",
            flush=True,
        )

        if args.show_trace:
            for h in state.history:
                line = f"    - {h.state} :: {h.name} :: {h.status}"
                if h.detail:
                    line += f" :: {json.dumps(h.detail, ensure_ascii=True)}"
                print(line, flush=True)
        print("-" * 80, flush=True)

    print(f"Done. evaluated={total}, correct={correct}, accuracy={correct / max(total, 1):.4f}", flush=True)


if __name__ == "__main__":
    main()

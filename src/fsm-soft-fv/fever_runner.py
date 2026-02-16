from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Tuple

from orchestrator import Orchestrator
from state import AgentState


DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "paper_dev.jsonl"


def _iter_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _predict_label(claim: str, step_callback: Callable[[Dict], None] | None = None) -> Tuple[str, AgentState]:
    state = AgentState(sid="fever", fsm="PARSE_CLAIM")
    orch = Orchestrator(state)
    try:
        orch.run(claim, step_callback=step_callback)
    except Exception:
        return "NOT ENOUGH INFO", state

    verdicts = [v.get("v") for v in state.verdicts if isinstance(v, dict)]
    if any(v == "refuted" for v in verdicts):
        return "REFUTES", state
    if verdicts and all(v == "supported" for v in verdicts):
        return "SUPPORTS", state
    return "NOT ENOUGH INFO", state


def _extract_evidence(state: AgentState, limit: int = 3) -> List[str]:
    if not state.evidence:
        return []
    selected_ids = {s.get("eid") for s in state.selected} if state.selected else set()
    ev_list = [e for e in state.evidence if e.eid in selected_ids] or list(state.evidence)
    lines = []
    for ev in ev_list[:limit]:
        text = (ev.s or "").strip()
        if text:
            lines.append(text)
    return lines


def _pick_rows(path: Path, start: int, limit: int, random_mode: bool, seed: int) -> List[Dict]:
    if random_mode:
        rows = list(_iter_jsonl(path))
        if start > 0:
            rows = rows[start:]
        rng = random.Random(seed)
        rng.shuffle(rows)
        return rows[:limit]

    picked = []
    for idx, row in enumerate(_iter_jsonl(path)):
        if idx < start:
            continue
        if len(picked) >= limit:
            break
        picked.append(row)
    return picked


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
    parser = argparse.ArgumentParser(description="Run soft-FSM fact verification on FEVER JSONL.")
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="Path to FEVER JSONL file.")
    parser.add_argument("--limit", type=int, default=20, help="Max rows to evaluate.")
    parser.add_argument("--start", type=int, default=0, help="Start row offset.")
    parser.add_argument("--random", action="store_true", help="Sample records randomly instead of sequential order.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used when --random is enabled.")
    parser.add_argument("--show-trace", action="store_true", help="Print step trace for each sample.")
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

    selected = _pick_rows(path, start=args.start, limit=args.limit, random_mode=args.random, seed=args.seed)

    total = 0
    correct = 0
    for row in selected:
        claim = row.get("claim", "")
        gold = row.get("label", "NOT ENOUGH INFO")
        sample_id = row.get("id")

        print(f"[{total + 1}] id={sample_id} | claim={claim}", flush=True)
        callback = _print_step if args.live_steps else None
        pred, state = _predict_label(claim, step_callback=callback)

        total += 1
        hit = pred == gold
        if hit:
            correct += 1
        acc = correct / total

        print(f"  model_judge={pred} | gold={gold} | correct={hit} | cumulative_acc={acc:.4f}", flush=True)

        if args.show_trace:
            for h in state.history:
                line = f"    - {h.state} :: {h.name} :: {h.status}"
                if h.detail:
                    line += f" :: {json.dumps(h.detail, ensure_ascii=True)}"
                print(line, flush=True)
            ev_lines = _extract_evidence(state)
            if ev_lines:
                print("  evidence:", flush=True)
                for line in ev_lines:
                    print(f"    - {line}", flush=True)
        print("-" * 80, flush=True)

    print(f"Done. evaluated={total}, correct={correct}, accuracy={correct / max(total, 1):.4f}", flush=True)


if __name__ == "__main__":
    main()

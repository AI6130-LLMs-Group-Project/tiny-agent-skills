### Wrapper to run FSM-based fact verification on FEVER dataset
### Please tell this runner the place of dataset JSONL file by --data argument

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, Iterable, Tuple

from orchestrator import Orchestrator
from state import AgentState


PRED_TO_FEVER = {
    "SUPPORT": "SUPPORTS",
    "REFUTE": "REFUTES",
    "NO ENOUGH INFO": "NOT ENOUGH INFO",
}


def _iter_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _predict_label(claim: str) -> Tuple[str, AgentState]:
    state = AgentState(sid="fever", fsm="PARSE_CLAIM")
    orch = Orchestrator(state)
    try:
        orch.run(claim)
    except Exception:
        return "NOT ENOUGH INFO", state

    verdicts = [v.get("v") for v in state.verdicts]
    if any(v == "refuted" for v in verdicts):
        return "REFUTES", state
    if any(v == "supported" for v in verdicts):
        return "SUPPORTS", state
    return "NOT ENOUGH INFO", state


# Main entry point: run on FEVER JSONL with given flags passing in args
def main() -> None:
    parser = argparse.ArgumentParser(description="Run FSM fact-verification pipeline on FEVER JSONL.")
    parser.add_argument("--data", default="data/paper_dev.jsonl", help="Path to FEVER JSONL file.")
    parser.add_argument("--limit", type=int, default=20, help="Max rows to evaluate.")
    parser.add_argument("--start", type=int, default=0, help="Start row offset.")
    parser.add_argument("--random", action="store_true", help="Sample records randomly instead of sequential order.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used when --random is enabled.")
    parser.add_argument("--show-trace", action="store_true", help="Print step trace for each sample.")
    args = parser.parse_args()

    path = Path(args.data)
    if not path.is_file():
        raise SystemExit(f"Dataset not found: {path}")

    if args.random:
        rows = list(_iter_jsonl(path))
        if args.start > 0:
            rows = rows[args.start:]
        rng = random.Random(args.seed)
        rng.shuffle(rows)
        selected = rows[: args.limit]
    else:
        selected = []
        for i, row in enumerate(_iter_jsonl(path)):
            if i < args.start:
                continue
            if len(selected) >= args.limit:
                break
            selected.append(row)

    total = 0
    correct = 0

    for row in selected:

        claim = row.get("claim", "")
        gold = row.get("label", "NOT ENOUGH INFO")
        pred, state = _predict_label(claim)

        total += 1
        hit = pred == gold
        if hit:
            correct += 1
        acc = correct / total

        print(f"[{total}] id={row.get('id')} | claim={claim}")
        print(f"  system={pred} | gold={gold} | correct={hit} | acc={acc:.4f}")
        if args.show_trace:
            for h in state.history:
                print(f"    - {h.state} :: {h.name} :: {h.status}")
        print("-" * 80)

    print(f"Done. evaluated={total}, correct={correct}, accuracy={correct/max(total,1):.4f}")


if __name__ == "__main__":
    main()

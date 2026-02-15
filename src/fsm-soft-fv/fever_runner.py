from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, Iterable, Tuple

from orchestrator import Orchestrator
from state import AgentState


def _iter_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _infer_label(state: AgentState) -> str:
    verdicts = [v.get("v") for v in state.verdicts if isinstance(v, dict)]
    if any(v == "refuted" for v in verdicts):
        return "REFUTES"
    if any(v == "supported" for v in verdicts):
        return "SUPPORTS"

    out = state.output if isinstance(state.output, dict) else {}
    rows = out.get("out") if isinstance(out.get("out"), list) else []
    labels = [r.get("ver") for r in rows if isinstance(r, dict)]
    if any(v == "refuted" for v in labels):
        return "REFUTES"
    if any(v == "supported" for v in labels):
        return "SUPPORTS"
    return "NOT ENOUGH INFO"


def _predict(claim: str) -> Tuple[str, AgentState]:
    state = AgentState(sid="fever", fsm="PARSE_CLAIM")
    orch = Orchestrator(state)
    try:
        orch.run(claim)
    except Exception:
        return "NOT ENOUGH INFO", state
    return _infer_label(state), state


def _default_data_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "data" / "paper_dev.jsonl"


def _extract_evidence(state: AgentState, limit: int = 3) -> str:
    if not state.evidence:
        return ""
    selected_ids = {x.get("eid") for x in state.selected if isinstance(x, dict)}
    pool = [e for e in state.evidence if e.eid in selected_ids] or list(state.evidence)
    lines = []
    for e in pool[:limit]:
        if e.s:
            lines.append(f"- {e.s}")
    return "\n".join(lines)


def _trace_line(rec) -> str:
    if rec.name != "controller":
        return f"    - {rec.state} :: {rec.name} :: {rec.status}"
    detail = rec.detail if isinstance(rec.detail, dict) else {}
    d = detail.get("d") if isinstance(detail.get("d"), dict) else {}
    analysis = d.get("analysis")
    next_action = d.get("next_action")
    if isinstance(analysis, str) and analysis.strip() and isinstance(next_action, str) and next_action.strip():
        return f"    - {rec.state} :: controller :: {analysis.strip()} -> next: {next_action.strip()}"
    if isinstance(analysis, str) and analysis.strip():
        return f"    - {rec.state} :: controller :: {analysis.strip()}"
    return f"    - {rec.state} :: controller :: {rec.status}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run soft-FSM fact verification on FEVER JSONL.")
    parser.add_argument("--data", default=str(_default_data_path()), help="Path to FEVER jsonl")
    parser.add_argument("--limit", type=int, default=20, help="Max rows to evaluate")
    parser.add_argument("--start", type=int, default=0, help="Start row offset")
    parser.add_argument("--random", action="store_true", help="Sample randomly")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--show-trace", action="store_true", help="Show state trace and evidence")
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
        pred, state = _predict(claim)
        total += 1
        hit = pred == gold
        if hit:
            correct += 1
        acc = correct / total

        print(f"[{total}] id={row.get('id')} | claim={claim}")
        print(f"  system={pred} | gold={gold} | correct={hit} | acc={acc:.4f}")
        if args.show_trace:
            for h in state.history:
                print(_trace_line(h))
            ev = _extract_evidence(state)
            if ev:
                print("  evidence:")
                print(ev)
        print("-" * 80)

    print(f"Done. evaluated={total}, correct={correct}, accuracy={correct/max(total,1):.4f}")


if __name__ == "__main__":
    main()

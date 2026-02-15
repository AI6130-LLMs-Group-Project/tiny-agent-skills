from __future__ import annotations

from typing import Any, Dict, List, Tuple

REQUIRED_TOP_KEYS = {"s", "d", "e", "rb"}


def sanitize(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {k: payload.get(k) for k in REQUIRED_TOP_KEYS}


def basic_check(payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "payload must be object"
    if payload.get("s") not in {"ok", "error", "retry"}:
        return False, "invalid status"
    if payload.get("rb") not in {"none", "state", "tools", None}:
        return False, "invalid rollback"
    return True, ""


def check_tool_output(payload: Any) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "tool payload must be object"
    if payload.get("s") not in {"ok", "error", "retry"}:
        return False, "tool payload missing valid status"
    if "d" not in payload:
        return False, "tool payload missing d"
    return True, ""


def check_controller_action(data: Any) -> Tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "controller d must be object"
    nxt = data.get("next")
    if not isinstance(nxt, str) or not nxt.strip():
        return False, "missing next state"
    analysis = data.get("analysis")
    if not isinstance(analysis, str) or not analysis.strip():
        return False, "missing analysis"
    next_action = data.get("next_action")
    if not isinstance(next_action, str) or not next_action.strip():
        return False, "missing next_action"
    call = data.get("call")
    if call is not None:
        if not isinstance(call, dict):
            return False, "call must be object or null"
        if not isinstance(call.get("tool"), str) or not call.get("tool").strip():
            return False, "call.tool must be non-empty string"
        if not isinstance(call.get("args", {}), dict):
            return False, "call.args must be object"
    write = data.get("write")
    if write is not None and not isinstance(write, dict):
        return False, "write must be object"
    done = data.get("done")
    if done is not None and not isinstance(done, bool):
        return False, "done must be bool"
    return True, ""


def extract_evidence_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("d")
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("results"), list):
        return data.get("results", [])
    if isinstance(data.get("items"), list):
        rows = []
        for i, item in enumerate(data.get("items", []), start=1):
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "rid": f"r{i}",
                    "snippet": item.get("text", ""),
                    "url": item.get("src", ""),
                    "src": "kb",
                    "d": item.get("d"),
                    "cred": item.get("cred", "med"),
                }
            )
        return rows
    if isinstance(data.get("sentences"), list):
        rows = []
        for i, item in enumerate(data.get("sentences", []), start=1):
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "rid": f"r{i}",
                    "snippet": item.get("s", ""),
                    "url": "",
                    "src": "extract",
                    "d": None,
                    "cred": "med",
                }
            )
        return rows
    return []


def trim_for_prompt(state_snapshot: Dict[str, Any], max_evidence: int = 20) -> Dict[str, Any]:
    out = dict(state_snapshot)
    ev = out.get("evidence")
    if isinstance(ev, list) and len(ev) > max_evidence:
        out["evidence"] = ev[-max_evidence:]
    return out

### This gatekeeper module performs basic validation and sanitization of tool outputs

from __future__ import annotations

from typing import Any, Dict, List, Tuple

### A reminder from Hanny:
# s -> status
# d -> data
# e -> error
# rb -> rollback
### Short entry name can save tokens in multi-round LLM calls. Suitable for my R7-6800 laptop :)
REQUIRED_TOP_KEYS = {"s", "d", "e", "rb"}


def basic_check(payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "payload must be object"
    if payload.get("s") not in {"ok", "error", "retry"}:
        return False, "invalid status"
    if payload.get("rb") not in {"none", "state", "tools", None}:
        return False, "invalid rollback"
    return True, ""


def sanitize(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    out = {k: payload.get(k) for k in REQUIRED_TOP_KEYS}
    return out


def check_tool_output(payload: Any) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "tool payload must be object"
    if "s" not in payload or payload.get("s") not in {"ok", "error", "retry"}:
        return False, "tool payload missing valid status"
    if "d" not in payload:
        return False, "tool payload missing d"
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

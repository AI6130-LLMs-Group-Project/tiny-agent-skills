from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, Iterable, List, Tuple


REQUIRED_TOP_KEYS = {"s", "d", "e", "rb"}
_VALID_STATUS = {"ok", "error", "retry"}
_VALID_RB = {"none", "state", "tools", None}


def basic_check(payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "payload must be object"
    if payload.get("s") not in _VALID_STATUS:
        return False, "invalid status"
    if payload.get("rb") not in _VALID_RB:
        return False, "invalid rollback"
    return True, ""


def sanitize(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {key: payload.get(key) for key in REQUIRED_TOP_KEYS}


def check_tool_output(payload: Any) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "tool payload must be object"
    if payload.get("s") not in _VALID_STATUS:
        return False, "tool payload missing valid status"
    if "d" not in payload:
        return False, "tool payload missing d"
    return True, ""


def extract_json_object(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj

    # Repair common small-model JSON issues: single quotes, trailing commas.
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}")
        candidate = text[start : end + 1]
        repaired = candidate.replace("“", '"').replace("”", '"').replace("’", "'")
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        try:
            obj, _ = decoder.raw_decode(repaired)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        try:
            lit = ast.literal_eval(repaired)
            if isinstance(lit, dict):
                return lit
        except Exception:
            pass
    raise ValueError("no valid JSON object found")


def check_action_payload(payload: Any, allowed_tools: Iterable[str]) -> Tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "action must be object"

    action = payload.get("a")
    if action not in {"tool", "advance", "finish"}:
        return False, "a must be tool|advance|finish"

    allowed = set(allowed_tools)
    if action == "tool":
        tool_name = payload.get("tool")
        if tool_name not in allowed:
            return False, "tool not allowed"
        args = payload.get("args")
        if args is None:
            payload["args"] = {}
        elif not isinstance(args, dict):
            return False, "args must be object"

    if action == "advance":
        if payload.get("status") not in {"ok", "retry", "back", "error"}:
            return False, "advance status must be ok|retry|back|error"

    return True, ""


def extract_evidence_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("d")
    if not isinstance(data, dict):
        return []

    if isinstance(data.get("results"), list):
        return data.get("results", [])

    if isinstance(data.get("items"), list):
        rows = []
        for idx, item in enumerate(data.get("items", []), start=1):
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "rid": f"r{idx}",
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
        for idx, item in enumerate(data.get("sentences", []), start=1):
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "rid": f"r{idx}",
                    "snippet": item.get("s", ""),
                    "url": "",
                    "src": "extract",
                    "d": None,
                    "cred": "med",
                }
            )
        return rows

    return []

from __future__ import annotations

import re
from typing import Any, Dict


def _err(code: str, msg: str) -> Dict[str, Any]:
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}}


def _ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"s": "ok", "d": data, "e": None}


def _coerce_num(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("bool is not numeric")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().replace(",", "")
    if not text:
        raise ValueError("empty value")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        raise ValueError("no numeric value found")
    return float(m.group(0))


def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Args:
      {"pred": number|string, "gold": number|string, "tol": float}
    Returns:
      {"s":"ok|error","d":{"pred":float,"gold":float,"delta":float,"match":bool},"e":...}
    """
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")
    tol = args.get("tol", 1e-6)
    try:
        tol = float(tol)
    except Exception:
        return _err("BAD_TOL", "tol must be numeric")
    if tol < 0:
        return _err("BAD_TOL", "tol must be >= 0")

    try:
        pred = _coerce_num(args.get("pred"))
        gold = _coerce_num(args.get("gold"))
    except Exception as exc:
        return _err("BAD_NUM", str(exc))

    delta = abs(pred - gold)
    return _ok({"pred": pred, "gold": gold, "delta": delta, "match": delta <= tol})

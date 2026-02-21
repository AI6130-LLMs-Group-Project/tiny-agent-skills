from __future__ import annotations

import re
from typing import Any, Dict, List, Set


def env_int(getter, name: str, default: int) -> int:
    try:
        return int(getter(name, default))
    except Exception:
        return default


def load_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def clean_text(text: str) -> str:
    text = (text or "").strip().strip("\"'`")
    return re.sub(r"\s+", " ", text)


def coerce_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError("bool is not int")
        if isinstance(value, (int, float)):
            out = int(value)
        else:
            out = int(str(value).strip())
        return max(lo, min(hi, out))
    except Exception:
        return default


def safe_claims(items: Any, fallback: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if isinstance(items, list):
        for i, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            cid = str(item.get("id") or f"s{i}")
            ctext = clean_text(str(item.get("c") or item.get("claim") or ""))
            if ctext:
                out.append({"id": cid, "c": ctext[:240]})
    if out:
        return out
    base = clean_text(fallback)[:240] or str(fallback)[:240]
    return [{"id": "s1", "c": base}]


def normalize_conf(value: Any) -> str:
    if isinstance(value, (int, float)):
        score = float(value)
        if score >= 0.75:
            return "high"
        if score >= 0.45:
            return "med"
        return "low"
    s = str(value or "").strip().lower()
    if s in {"high", "h", "strong", "certain"}:
        return "high"
    if s in {"med", "medium", "m", "moderate"}:
        return "med"
    if s in {"low", "l", "weak", "uncertain"}:
        return "low"
    try:
        return normalize_conf(float(s))
    except Exception:
        return "low"


def normalize_stance(value: Any) -> str:
    s = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    if s in {"support", "supports", "supported", "entailment", "entails", "true"}:
        return "support"
    if s in {"refute", "refutes", "refuted", "contradiction", "contradicts", "false"}:
        return "refute"
    if s in {"neutral", "unknown", "nei", "not enough info", "insufficient"}:
        return "neutral"
    return ""


def normalize_verdict(value: Any) -> str:
    s = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    if s in {"support", "supports", "supported", "true"}:
        return "supported"
    if s in {"refute", "refutes", "refuted", "false"}:
        return "refuted"
    if s in {"mixed", "conflict", "conflicted"}:
        return "mixed"
    if s in {"neutral", "unknown", "nei", "not enough info", "insufficient"}:
        return "insufficient"
    return ""


def to_query_list(raw: Any, max_items: int = 4, max_tokens: int = 8) -> List[str]:
    rows: List[str] = []
    if isinstance(raw, str):
        rows = [raw]
    elif isinstance(raw, list):
        for x in raw:
            if isinstance(x, str):
                rows.append(x)
            elif isinstance(x, dict):
                q = x.get("q") or x.get("query")
                if isinstance(q, str):
                    rows.append(q)
    elif isinstance(raw, dict):
        q = raw.get("q") or raw.get("query")
        if isinstance(q, str):
            rows = [q]
    out: List[str] = []
    seen: Set[str] = set()
    for q in rows:
        qq = " ".join(str(q).strip().split()[:max_tokens])
        if qq and qq not in seen:
            seen.add(qq)
            out.append(qq)
        if len(out) >= max_items:
            break
    return out


def first_list(obj: Dict[str, Any], keys: List[str]) -> List[Any]:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, list):
            return v
    return []


def first_dict(obj: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, dict):
            return v
    return {}

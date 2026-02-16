from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple


STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "to", "of", "in", "on", "at",
    "for", "from", "by", "as", "that", "this", "it", "its", "and", "or", "with", "during", "into", "over",
    "under", "than", "then", "who", "what", "when", "where", "which",
}


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


def fallback_parse(claim: str) -> Dict[str, Any]:
    text = clean_text(claim)
    ct = "atomic"
    if text.endswith("?"):
        ct = "question"
        text = text[:-1].strip()
    if " and " in text.lower() or " or " in text.lower() or ";" in text:
        ct = "multi"
    if text and text[-1] not in ".!?":
        text += "."
    subs: List[Dict[str, str]] = []
    if ct == "multi":
        parts = re.split(r"\s+(?:and|or)\s+", text.rstrip("."), flags=re.IGNORECASE)
        for i, p in enumerate(parts, start=1):
            pp = clean_text(p)
            if pp:
                if pp[-1] not in ".!?":
                    pp += "."
                subs.append({"id": f"s{i}", "c": pp[:240]})
    return {"nc": text[:240], "ct": ct, "sd": ct == "multi", "subs": subs}


def fallback_query_plans(claims: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    plans: List[Dict[str, Any]] = []
    for c in claims:
        text = c.get("c", "")
        ent = re.findall(r"(?:\b[A-Z][a-z]+\b(?:\s+\b[A-Z][a-z]+\b){0,2})", text)
        yrs = re.findall(r"\b\d{4}\b", text)
        toks = [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]
        candidates = [
            " ".join(([ent[0]] if ent else []) + toks[:3] + yrs).strip(),
            " ".join(([ent[0]] if ent else []) + yrs).strip(),
        ]
        out_q = to_query_list(candidates, max_items=2, max_tokens=8)
        plans.append({"id": c.get("id", "s1"), "q": out_q or [text[:80]], "lim": 3})
    return plans


def fallback_select(claims: List[Dict[str, str]], ev_rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    claim_map = {c.get("id", ""): c.get("c", "") for c in claims}
    ranked: List[Tuple[int, Any, Any]] = []
    for row in ev_rows:
        cid = row.get("for", "")
        claim = claim_map.get(cid, "")
        sent = row.get("s", "")
        if not claim or not sent:
            continue
        c_terms = set(re.findall(r"[a-z0-9]+", claim.lower()))
        s_terms = set(re.findall(r"[a-z0-9]+", sent.lower()))
        ov = len(c_terms.intersection(s_terms))
        if ov > 0:
            ranked.append((ov, row.get("eid"), cid))
    ranked.sort(key=lambda x: (-x[0], str(x[1])))
    return [{"eid": eid, "for": cid} for _, eid, cid in ranked[:5] if eid and cid]


def fallback_nli(claims: List[Dict[str, str]], sel_rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    claim_map = {c.get("id", ""): c.get("c", "") for c in claims}
    out: List[Dict[str, str]] = []
    for row in sel_rows:
        cid = row.get("for", "")
        claim = claim_map.get(cid, "")
        sent = row.get("s", "")
        if not claim or not sent:
            continue
        c_terms = {t for t in re.findall(r"[a-z0-9]+", claim.lower()) if t not in STOPWORDS}
        s_terms = {t for t in re.findall(r"[a-z0-9]+", sent.lower()) if t not in STOPWORDS}
        overlap = len(c_terms.intersection(s_terms))
        ratio = overlap / max(1, len(c_terms))
        c_neg = any(x in f" {claim.lower()} " for x in [" not ", " never ", " no ", "n't"])
        s_neg = any(x in f" {sent.lower()} " for x in [" not ", " never ", " no ", "n't"])
        if overlap < 1 or ratio < 0.15:
            st, conf = "neutral", "low"
        elif c_neg != s_neg and ratio >= 0.25:
            st, conf = "refute", "med"
        elif ratio >= 0.55:
            st, conf = "support", "high"
        elif ratio >= 0.35:
            st, conf = "support", "med"
        else:
            st, conf = "neutral", "low"
        out.append({"eid": row.get("eid", ""), "for": cid, "st": st, "conf": conf})
    return out


def fallback_decide(claims: List[Dict[str, str]], scores: List[Dict[str, str]]) -> List[Dict[str, str]]:
    def w(conf: str) -> float:
        return 2.0 if conf == "high" else 1.0 if conf == "med" else 0.5

    by_claim: Dict[str, List[Dict[str, str]]] = {}
    for sc in scores:
        by_claim.setdefault(sc.get("for", ""), []).append(sc)
    out: List[Dict[str, str]] = []
    for c in claims:
        cid = c.get("id", "s1")
        grp = by_claim.get(cid, [])
        support = sum(w(x.get("conf", "low")) for x in grp if x.get("st") == "support")
        refute = sum(w(x.get("conf", "low")) for x in grp if x.get("st") == "refute")
        if refute >= max(1.5, support + 0.5):
            v, conf = "refuted", "high" if refute >= 2.5 else "med"
        elif support >= max(1.8, refute + 0.7):
            v, conf = "supported", "high" if support >= 3.0 else "med"
        elif support > 0 and refute > 0:
            v, conf = "mixed", "low"
        else:
            v, conf = "insufficient", "low"
        out.append({"id": cid, "v": v, "conf": conf})
    return out


def fallback_output(claims: List[Dict[str, str]], verdicts: List[Dict[str, str]], selected: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    verdict_map = {v.get("id", ""): v for v in verdicts}
    cite_map: Dict[str, List[str]] = {}
    for s in selected:
        cid, eid = s.get("for", ""), s.get("eid", "")
        if cid and eid:
            cite_map.setdefault(cid, []).append(eid)
    out: List[Dict[str, Any]] = []
    for c in claims:
        cid = c.get("id", "s1")
        vv = verdict_map.get(cid, {"v": "insufficient", "conf": "low"})
        verdict = vv.get("v", "insufficient")
        if verdict == "supported":
            reason = "Selected evidence supports the claim."
        elif verdict == "refuted":
            reason = "Selected evidence contradicts the claim."
        elif verdict == "mixed":
            reason = "Evidence is mixed and cannot fully resolve the claim."
        else:
            reason = "Evidence is insufficient for a reliable judgment."
        out.append({"id": cid, "ver": verdict, "conf": vv.get("conf", "low"), "r": reason[:220], "cite": cite_map.get(cid, [])[:2]})
    return out

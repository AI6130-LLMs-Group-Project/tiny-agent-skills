### Tool to rate NLI scores for claim-evidence pairs

import re


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


def _tokens(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _years(text):
    return set(re.findall(r"\b(1[5-9]\d{2}|20\d{2}|2100)\b", text or ""))


def _has_negation(text):
    t = (text or "").lower()
    neg_words = [" not ", " never ", " no ", " none ", "n't", "without "]
    return any(w in f" {t} " for w in neg_words)


def _score_pair(claim, sent):
    c_toks = set(_tokens(claim))
    s_toks = set(_tokens(sent))
    if not c_toks or not s_toks:
        return "neutral", "low"

    overlap = len(c_toks.intersection(s_toks))
    ratio = overlap / max(1, min(len(c_toks), len(s_toks)))

    cy = _years(claim)
    sy = _years(sent)
    if cy and sy and cy.isdisjoint(sy):
        return "refute", "med"

    c_neg = _has_negation(claim)
    s_neg = _has_negation(sent)
    if c_neg != s_neg and ratio >= 0.35:
        return "refute", "med"

    if ratio >= 0.5:
        return "support", "high"
    if ratio >= 0.3:
        return "support", "med"
    return "neutral", "low"


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")

    claims = args.get("claims")
    sel = args.get("sel")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}
    if not isinstance(claims, list) or not isinstance(sel, list):
        return _err("BAD_INPUT", "claims and sel must be lists")
    if not sel:
        return _err("NO_SELECTED", "sel is empty")

    claim_map = {}
    for c in claims:
        if isinstance(c, dict):
            claim_map[c.get("id", "")] = c.get("c", "")

    scores = []
    for item in sel:
        if not isinstance(item, dict):
            continue
        cid = item.get("for", "")
        claim = claim_map.get(cid, "")
        sent = item.get("s", "")
        stance, conf = _score_pair(claim, sent)
        scores.append({"eid": item.get("eid", ""), "for": cid, "st": stance, "conf": conf})

    if not scores:
        return _err("NO_VALID_SELECTED", "no valid selected evidence")

    rev = int(st.get("rev", 0)) + 1
    return _ok({"scores": scores, "sp": {"rev": rev, "fsm": "NLI_VERIFY"}})

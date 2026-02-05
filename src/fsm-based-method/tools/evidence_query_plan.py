### Tool for planning evidence tool queries based on claim

import re


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "to", "of", "in", "on", "at",
    "for", "from", "by", "as", "that", "this", "it", "its", "and", "or", "with", "during", "into", "over",
    "under", "than", "then", "who", "what", "when", "where", "which",
}


def _tokens(text):
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in toks if t not in _STOP]


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")
    claims = args.get("claims")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}
    if not isinstance(claims, list) or not claims:
        return _err("NO_CLAIMS", "claims is empty")

    plans = []
    for c in claims:
        if not isinstance(c, dict):
            continue
        cid = c.get("id", "s1")
        claim_text = c.get("c", "")
        toks = _tokens(claim_text)
        q = " ".join(toks[:6]) if toks else claim_text[:60]
        if not q:
            continue
        plans.append({"id": cid, "q": [q], "src": ["wiki", "kb", "web"], "lim": 4})

    if not plans:
        return _err("NO_QUERIES", "no valid query")
    rev = int(st.get("rev", 0)) + 1
    return _ok({"plans": plans, "sp": {"rev": rev, "fsm": "RETRIEVAL"}})

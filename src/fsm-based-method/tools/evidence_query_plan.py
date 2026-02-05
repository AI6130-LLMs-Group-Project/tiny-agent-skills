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


def _entity_phrases(text):
    if not text:
        return []
    # Capture Title Case spans and mixed-case tokens (e.g., CHiPs, iPhone).
    spans = re.findall(r"(?:\b[A-Z][a-z]+\b(?:\s+\b[A-Z][a-z]+\b){0,3})", text)
    mixed = re.findall(r"\b[A-Za-z]*[A-Z][A-Za-z]*\b", text)
    phrases = []
    for s in spans:
        s = s.strip()
        if s and s not in phrases:
            phrases.append(s)
    for m in mixed:
        if len(m) >= 2 and m not in phrases:
            phrases.append(m)
    return phrases


def _predicate_terms(text):
    # Non-entity content words.
    ent = set(t.lower() for t in _entity_phrases(text))
    terms = []
    for t in _tokens(text):
        if t in ent:
            continue
        terms.append(t)
    return terms


def _dedupe(seq):
    seen = set()
    out = []
    for s in seq:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _limit_tokens(q, max_tokens=6):
    parts = q.split()
    if len(parts) <= max_tokens:
        return q
    return " ".join(parts[:max_tokens])


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
        ents = _entity_phrases(claim_text)
        preds = _predicate_terms(claim_text)
        queries = []

        if ents:
            ent = ents[0].strip()
            if ent:
                queries.append(ent)
                if preds:
                    queries.append(" ".join([ent] + preds[:2]))
        else:
            toks = _tokens(claim_text)
            if toks:
                queries.append(" ".join(toks[:6]))

        queries = [_limit_tokens(q) for q in queries if q]
        queries = _dedupe(queries)[:2]
        if not queries:
            continue
        plans.append({"id": cid, "q": queries, "src": ["wiki", "kb", "web"], "lim": 4})

    if not plans:
        return _err("NO_QUERIES", "no valid query")
    rev = int(st.get("rev", 0)) + 1
    return _ok({"plans": plans, "sp": {"rev": rev, "fsm": "RETRIEVAL"}})

import re


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}}


def _ok(data):
    return {"s": "ok", "d": data, "e": None}


def _split_sentences(text):
    # Not fancy NLP, just sturdy enough for wiki-ish pages.
    chunks = re.split(r"(?<=[.!?])\s+", text or "")
    out = []
    for chunk in chunks:
        s = " ".join(chunk.strip().split())
        if len(s) < 20:
            continue
        out.append(s)
    return out


def _tokenize(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")

    text = args.get("text")
    query = args.get("query")
    top_n = args.get("top_n", 3)

    if not isinstance(text, str) or not text.strip():
        return _err("BAD_TEXT", "text must be non-empty string")
    if not isinstance(query, str) or not query.strip():
        return _err("BAD_QUERY", "query must be non-empty string")
    if not isinstance(top_n, int) or top_n < 1 or top_n > 10:
        return _err("BAD_TOP_N", "top_n must be 1..10")

    q_terms = _tokenize(query)
    rows = []
    for sent in _split_sentences(text):
        s_terms = _tokenize(sent)
        overlap = len(q_terms.intersection(s_terms))
        if overlap <= 0:
            continue
        rows.append((overlap, sent))

    rows.sort(key=lambda x: (-x[0], len(x[1])))
    out = [{"s": sent, "score": score} for score, sent in rows[:top_n]]
    return _ok({"sentences": out})

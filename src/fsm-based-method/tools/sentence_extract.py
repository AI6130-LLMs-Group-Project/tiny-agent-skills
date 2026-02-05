### This tool extracts the most relevant sentences from a given text based on an optional query

import json
import math
import os
import re
from html import unescape


_TOP_N_DEFAULT = 3


def _load_runtime_env():
    if getattr(_load_runtime_env, "_loaded", False):
        return
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(root, ".env")
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k and k not in os.environ:
                    os.environ[k] = v
    _load_runtime_env._loaded = True


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}}


def _ok(data):
    return {"s": "ok", "d": data, "e": None}


def _clean_text(text):
    if text is None:
        return ""
    text = unescape(str(text))
    # Strip scripts/styles to avoid noisy tokens.
    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", text)
    # Strip HTML tags and common citation markers.
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[[^\]]+\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _sent_split(text):
    text = _clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[\.!\?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _tok(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _bm25_scores(sentences, query_terms):
    if not sentences or not query_terms:
        return [0.0] * len(sentences)
    k1 = 1.2
    b = 0.75
    docs = [ _tok(s) for s in sentences ]
    avgdl = sum(len(d) for d in docs) / max(1, len(docs))
    idf = {}
    for term in set(query_terms):
        df = sum(1 for d in docs if term in d)
        idf[term] = math.log(1 + (len(docs) - df + 0.5) / (df + 0.5))
    scores = []
    for d in docs:
        score = 0.0
        dl = len(d)
        for term in query_terms:
            tf = d.count(term)
            if tf == 0:
                continue
            denom = tf + k1 * (1 - b + b * (dl / avgdl))
            score += idf.get(term, 0.0) * (tf * (k1 + 1) / denom)
        scores.append(score)
    return scores


def run(args):
    """
    Args schema:
        {"text": str, "query": str|null, "top_n": int|null}

    Returns:
        {"s": "ok|error", "d": {"sentences": [{"i": int, "s": str, "score": float}]}, "e": {..}|None}
    """
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be an object")
    _load_runtime_env()
    text = (args.get("text") or "").strip()
    query = (args.get("query") or "").strip()
    top_n = args.get("top_n")
    if top_n is None:
        env_top_n = os.getenv("TOP_N")
        if env_top_n and env_top_n.isdigit():
            top_n = int(env_top_n)
        else:
            top_n = _TOP_N_DEFAULT
    if not isinstance(top_n, int) or top_n < 1 or top_n > 10:
        return _err("BAD_TOP_N", "top_n must be 1..10")
    if not text:
        return _err("EMPTY_TEXT", "text is required")

    sents = _sent_split(text)
    if not sents:
        return _err("NO_SENTENCES", "no sentences found")

    if query:
        q_terms = _tok(query)
        scores = _bm25_scores(sents, q_terms)
    else:
        scores = [0.0] * len(sents)

    ranked = sorted(
        enumerate(zip(sents, scores)),
        key=lambda x: (-x[1][1], x[0]),
    )

    out = []
    for idx, (sent, score) in ranked[:top_n]:
        out.append({"i": idx, "s": sent, "score": score})

    return _ok({"sentences": out})

# Quick test lah
if __name__ == "__main__":
    sample = {"text": "Apollo 11 landed on the Moon. It launched in 1969.", "query": "Apollo 11 1969", "top_n": 2}
    print(json.dumps(run(sample), ensure_ascii=True))

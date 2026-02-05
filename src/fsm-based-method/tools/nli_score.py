### Tool to rate NLI scores for claim-evidence pairs (conservative / contradiction-first, now with parameters)

import os
import re


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


def _tokens(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _years(text):
    return set(re.findall(r"\b(1[5-9]\d{2}|20\d{2}|2100)\b", text or ""))


def _numbers(text):
    return set(re.findall(r"\b\d+\b", text or ""))


def _has_negation(text):
    t = (text or "").lower()
    neg_words = [" not ", " never ", " no ", " none ", "n't", "without "]
    return any(w in f" {t} " for w in neg_words)


_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "to", "of", "in", "on", "at",
    "for", "from", "by", "as", "that", "this", "it", "its", "and", "or", "with", "during", "into", "over",
    "under", "than", "then", "who", "what", "when", "where", "which",
}

_OPPOSITE_PAIRS = [
    ("born", "died"),
    ("win", "lose"),
    ("won", "lost"),
    ("accept", "reject"),
    ("accepted", "rejected"),
    ("support", "oppose"),
    ("supports", "opposes"),
    ("allow", "ban"),
    ("allowed", "banned"),
]


def _content_tokens(text):
    toks = _tokens(text)
    return [t for t in toks if t not in _STOPWORDS]


def _has_opposite_pair(claim, sent):
    c = f" {_normalize_text(claim)} "
    s = f" {_normalize_text(sent)} "
    for a, b in _OPPOSITE_PAIRS:
        if (f" {a} " in c and f" {b} " in s) or (f" {b} " in c and f" {a} " in s):
            return True
    return False


def _normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

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


def _env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default


def _env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default


def _score_pair(claim, sent):
    _load_runtime_env()
    neutral_ratio = _env_float("NLI_NEUTRAL_RATIO", 0.18)
    neutral_overlap = _env_int("NLI_NEUTRAL_OVERLAP", 1)
    neg_refute_ratio = _env_float("NLI_NEG_REFUTE_RATIO", 0.28)
    opp_refute_ratio = _env_float("NLI_OPP_REFUTE_RATIO", 0.25)
    support_high_ratio = _env_float("NLI_SUPPORT_HIGH_RATIO", 0.55)
    support_med_ratio = _env_float("NLI_SUPPORT_MED_RATIO", 0.38)

    c_toks = set(_content_tokens(claim))
    s_toks = set(_content_tokens(sent))
    if not c_toks or not s_toks:
        return "neutral", "low"

    overlap = len(c_toks.intersection(s_toks))
    ratio = overlap / max(1, len(c_toks))

    # Low overlap should not be SUPPORT.
    if overlap < neutral_overlap or ratio < neutral_ratio:
        return "neutral", "low"

    cy = _years(claim)
    sy = _years(sent)
    if cy and sy and cy.isdisjoint(sy):
        return "refute", "high"

    cn = _numbers(claim)
    sn = _numbers(sent)
    # If claim has numbers and sentence has numbers but they disagree, treat as contradiction.
    if cn and sn and not cn.issubset(sn):
        # Only refute when the sentence has numbers but does not contain the claim numbers.
        return "refute", "med"

    c_neg = _has_negation(claim)
    s_neg = _has_negation(sent)
    if c_neg != s_neg and ratio >= neg_refute_ratio:
        return "refute", "high"

    if _has_opposite_pair(claim, sent) and ratio >= opp_refute_ratio:
        return "refute", "high"

    # Support needs decent overlap but not extreme.
    if ratio >= support_high_ratio:
        return "support", "high"
    if ratio >= support_med_ratio:
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
        # Trust calibration: if source cred is low, cap confidence to low.
        cred = (item.get("cred") or "med").lower()
        if cred == "low":
            conf = "low"
        scores.append({"eid": item.get("eid", ""), "for": cid, "st": stance, "conf": conf})

    if not scores:
        return _err("NO_VALID_SELECTED", "no valid selected evidence")

    rev = int(st.get("rev", 0)) + 1
    return _ok({"scores": scores, "sp": {"rev": rev, "fsm": "NLI_VERIFY"}})

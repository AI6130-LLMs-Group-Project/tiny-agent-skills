### Tool to rate NLI scores for claim-evidence pairs (conservative / contradiction-first, now with parameters)

import os
import re
from pathlib import Path


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


_SYNONYMS = {
    "born": "birth",
    "birth": "birth",
    "died": "death",
    "death": "death",
    "married": "marry",
    "marriage": "marry",
    "released": "release",
    "release": "release",
    "wins": "win",
    "won": "win",
    "loses": "lose",
    "lost": "lose",
    "founded": "found",
    "founding": "found",
    "invented": "invent",
    "inventor": "invent",
}


def _normalize_token(tok):
    t = tok.lower()
    if t.endswith("'s"):
        t = t[:-2]
    # Light stemming to improve overlap without extra deps.
    for suf in ("ing", "ed", "es", "s"):
        if t.endswith(suf) and len(t) > len(suf) + 2:
            t = t[: -len(suf)]
            break
    return _SYNONYMS.get(t, t)


def _content_tokens(text):
    toks = _tokens(text)
    out = []
    for t in toks:
        if t in _STOPWORDS:
            continue
        out.append(_normalize_token(t))
    return out


def _entity_tokens(text):
    if not text:
        return set()
    spans = re.findall(r"(?:\b[A-Z][a-z]+\b(?:\s+\b[A-Z][a-z]+\b){0,3})", text)
    mixed = re.findall(r"\b[A-Za-z]*[A-Z][A-Za-z]*\b", text)
    ents = set()
    for s in spans:
        for t in s.split():
            if len(t) >= 2:
                ents.add(_normalize_token(t))
    for m in mixed:
        if len(m) >= 2:
            ents.add(_normalize_token(m))
    return ents

def _predicate_terms(text):
    ents = _entity_tokens(text)
    toks = set(_content_tokens(text))
    return {t for t in toks if t not in ents}



def _has_opposite_pair(claim, sent):
    c = f" {_normalize_text(claim)} "
    s = f" {_normalize_text(sent)} "
    for a, b in _OPPOSITE_PAIRS:
        if (f" {a} " in c and f" {b} " in s) or (f" {b} " in c and f" {a} " in s):
            return True
    return False


def _only_refute(claim, sent):
    c = _normalize_text(claim)
    if " only " not in f" {c} " and " sole " not in f" {c} ":
        return False
    claim_ents = _entity_tokens(claim)
    sent_ents = _entity_tokens(sent)
    if not claim_ents or not sent_ents:
        return False
    extra = {e for e in sent_ents if e not in claim_ents}
    if len(extra) >= 2 and any(e in sent_ents for e in claim_ents):
        return True
    return False


def _normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def _copular_claim(text):
    t = _normalize_text(text).rstrip(".")
    m = re.match(r"(.+?)\s+(is|was|are|were)\s+(an?|the)\s+(.+)$", t)
    if not m:
        return None
    subj = m.group(1).strip()
    pred = m.group(4).strip()
    if not subj or not pred:
        return None
    return subj, pred


def _evidence_matches_copular(subj, pred, sent):
    if not subj or not pred or not sent:
        return False
    subj_terms = _content_tokens(subj)
    pred_terms = _content_tokens(pred)
    if not subj_terms or not pred_terms:
        return False
    sent_terms = set(_content_tokens(sent))
    subj_need = 2 if len(subj_terms) >= 3 else 1
    subj_hits = sum(1 for t in subj_terms if t in sent_terms)
    pred_hits = sum(1 for t in pred_terms if t in sent_terms)
    if subj_hits < subj_need or pred_hits < 1:
        return False
    s_norm = f" {_normalize_text(sent)} "
    if any(f" {v} " in s_norm for v in ("is", "was", "are", "were")):
        return True
    if re.search(r",\s+(an?|the)\s+\w+", s_norm):
        return True
    return False


def _load_runtime_env():
    if getattr(_load_runtime_env, "_loaded", False):
        return
    root = Path(__file__).resolve().parents[3]
    env_path = root / ".env"
    if env_path.is_file():
        with env_path.open("r", encoding="utf-8") as f:
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
    neutral_ratio = _env_float("NLI_NEUTRAL_RATIO", 0.15)
    neutral_overlap = _env_int("NLI_NEUTRAL_OVERLAP", 1)
    neg_refute_ratio = _env_float("NLI_NEG_REFUTE_RATIO", 0.25)
    opp_refute_ratio = _env_float("NLI_OPP_REFUTE_RATIO", 0.22)
    num_refute_ratio = _env_float("NLI_NUM_REFUTE_RATIO", 0.25)
    year_refute_ratio = _env_float("NLI_YEAR_REFUTE_RATIO", 0.2)
    support_high_ratio = _env_float("NLI_SUPPORT_HIGH_RATIO", 0.5)
    support_med_ratio = _env_float("NLI_SUPPORT_MED_RATIO", 0.32)

    c_toks = set(_content_tokens(claim))
    s_toks = set(_content_tokens(sent))
    if not c_toks or not s_toks:
        return "neutral", "low"

    overlap = len(c_toks.intersection(s_toks))
    ratio = overlap / max(1, len(c_toks))

    # Low overlap should not be SUPPORT.
    if overlap < neutral_overlap or ratio < neutral_ratio:
        return "neutral", "low"

    cop = _copular_claim(claim)
    if cop:
        subj, pred = cop
        if not _evidence_matches_copular(subj, pred, sent):
            return "neutral", "low"

    cy = _years(claim)
    sy = _years(sent)
    if cy and not sy:
        return "neutral", "low"
    if cy and sy and cy.isdisjoint(sy) and ratio >= year_refute_ratio:
        pred_terms = _predicate_terms(claim)
        if pred_terms and pred_terms.intersection(s_toks):
            return "refute", "high"
        return "neutral", "low"

    cn = _numbers(claim)
    sn = _numbers(sent)
    if cn and not sn:
        return "neutral", "low"
    # If claim has numbers and sentence has numbers but they disagree, treat as contradiction.
    if cn and sn and cn.isdisjoint(sn) and ratio >= num_refute_ratio:
        return "refute", "med"

    c_neg = _has_negation(claim)
    s_neg = _has_negation(sent)
    if c_neg != s_neg and ratio >= neg_refute_ratio:
        return "refute", "high"

    if _has_opposite_pair(claim, sent) and ratio >= opp_refute_ratio:
        return "refute", "high"
    if _only_refute(claim, sent):
        return "refute", "high"

    # Quick substring match is a strong support signal.
    if _normalize_text(claim) in _normalize_text(sent):
        return "support", "high"

    # If named entities don't appear in evidence, stay conservative.
    ents = _entity_tokens(claim)
    if ents:
        sent_lower = (sent or "").lower()
        if not any(e in sent_lower for e in ents) and overlap < 2:
            return "neutral", "low"

    # Require predicate overlap for support.
    pred_terms = {t for t in c_toks if t not in ents}
    if pred_terms and not (pred_terms & s_toks):
        return "neutral", "low"

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

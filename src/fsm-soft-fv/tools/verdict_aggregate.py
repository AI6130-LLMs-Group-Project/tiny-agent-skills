def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


def _w(conf):
    if conf == "high":
        return 2.0
    if conf == "med":
        return 1.0
    return 0.5


def _decide(group):
    import os

    def _env_float(name, default):
        try:
            return float(os.getenv(name, default))
        except Exception:
            return default

    support_score = sum(_w(x.get("conf")) for x in group if x.get("st") == "support")
    refute_score = sum(_w(x.get("conf")) for x in group if x.get("st") == "refute")
    neutral_count = sum(1 for x in group if x.get("st") == "neutral")

    refute_min = _env_float("DECIDE_REFUTE_MIN", 1.5)
    refute_margin = _env_float("DECIDE_REFUTE_MARGIN", 0.5)
    refute_high = _env_float("DECIDE_REFUTE_HIGH", 2.5)
    support_min = _env_float("DECIDE_SUPPORT_MIN", 1.8)
    support_margin = _env_float("DECIDE_SUPPORT_MARGIN", 0.7)
    support_high = _env_float("DECIDE_SUPPORT_HIGH", 3.0)

    if refute_score >= max(refute_min, support_score + refute_margin):
        conf = "high" if refute_score >= refute_high else "med"
        return "refuted", conf
    if support_score >= max(support_min, refute_score + support_margin):
        conf = "high" if support_score >= support_high else "med"
        return "supported", conf
    if support_score > 0 and refute_score > 0:
        return "mixed", "low"
    if neutral_count > 0:
        return "insufficient", "low"
    return "insufficient", "low"


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")

    claims = args.get("claims")
    scores = args.get("scores")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}
    if not isinstance(claims, list) or not isinstance(scores, list):
        return _err("BAD_INPUT", "claims and scores must be lists")

    by_claim = {}
    for score in scores:
        if not isinstance(score, dict):
            continue
        cid = score.get("for", "")
        by_claim.setdefault(cid, []).append(score)

    out = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        cid = claim.get("id", "s1")
        verdict, conf = _decide(by_claim.get(cid, []))
        out.append({"id": cid, "v": verdict, "conf": conf})

    rev = int(st.get("rev", 0)) + 1
    return _ok({"ver": out, "sp": {"rev": rev, "fsm": "DECIDE"}})

### Verdictt aggregation (conservative against false SUPPORT)


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

    s_score = sum(_w(x.get("conf")) for x in group if x.get("st") == "support")
    r_score = sum(_w(x.get("conf")) for x in group if x.get("st") == "refute")
    n_count = sum(1 for x in group if x.get("st") == "neutral")

    # Conservative: support must clearly dominate; contradiction has priority.
    r_min = _env_float("DECIDE_REFUTE_MIN", 1.5)
    r_margin = _env_float("DECIDE_REFUTE_MARGIN", 0.5)
    r_high = _env_float("DECIDE_REFUTE_HIGH", 2.5)
    s_min = _env_float("DECIDE_SUPPORT_MIN", 1.8)
    s_margin = _env_float("DECIDE_SUPPORT_MARGIN", 0.7)
    s_high = _env_float("DECIDE_SUPPORT_HIGH", 3.0)

    if r_score >= max(r_min, s_score + r_margin):
        conf = "high" if r_score >= r_high else "med"
        return "refuted", conf
    if s_score >= max(s_min, r_score + s_margin):
        conf = "high" if s_score >= s_high else "med"
        return "supported", conf
    if s_score > 0 and r_score > 0:
        return "mixed", "low"
    if n_count > 0:
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
    for sc in scores:
        if not isinstance(sc, dict):
            continue
        cid = sc.get("for", "")
        by_claim.setdefault(cid, []).append(sc)

    out = []
    for c in claims:
        if not isinstance(c, dict):
            continue
        cid = c.get("id", "s1")
        vv, cc = _decide(by_claim.get(cid, []))
        out.append({"id": cid, "v": vv, "conf": cc})

    rev = int(st.get("rev", 0)) + 1
    return _ok({"ver": out, "sp": {"rev": rev, "fsm": "DECIDE"}})

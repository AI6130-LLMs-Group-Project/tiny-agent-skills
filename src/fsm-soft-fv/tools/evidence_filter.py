import re


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _score(claim, evidence_text):
    claim_terms = _tokens(claim)
    ev_terms = _tokens(evidence_text)
    if not claim_terms or not ev_terms:
        return 0
    return len(claim_terms.intersection(ev_terms))


def _cred_weight(cred):
    if cred == "high":
        return 0.3
    if cred == "med":
        return 0.1
    return 0.0


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")

    claims = args.get("claims")
    evidence = args.get("ev")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}

    if not isinstance(claims, list) or not isinstance(evidence, list):
        return _err("BAD_INPUT", "claims and ev must be lists")
    if not evidence:
        return _err("NO_EVIDENCE", "ev is empty")

    claim_map = {}
    for claim in claims:
        if isinstance(claim, dict):
            claim_map[claim.get("id", "")] = claim.get("c", "")

    scored = []
    for row in evidence:
        if not isinstance(row, dict):
            continue
        cid = row.get("for", "")
        text = row.get("s", "")
        claim_text = claim_map.get(cid, "")
        if not claim_text or not text:
            continue
        base = _score(claim_text, text)
        if base <= 0:
            continue
        bonus = _cred_weight((row.get("cred") or "med").lower())
        scored.append((base + bonus, row.get("eid"), cid))

    if not scored:
        return {"s": "retry", "d": {"sel": [], "drop": [], "sp": {"rev": int(st.get("rev", 0)) + 1, "fsm": "SELECT_EVIDENCE"}}, "e": {"code": "NO_MATCH", "msg": "no evidence overlap"}, "rb": "state"}

    scored.sort(key=lambda x: (-x[0], str(x[1]), str(x[2])))
    selected = [{"eid": eid, "for": cid} for _, eid, cid in scored[:5] if eid]
    selected_ids = {item["eid"] for item in selected}

    drop = []
    for row in evidence:
        if not isinstance(row, dict):
            continue
        eid = row.get("eid")
        if eid and eid not in selected_ids:
            drop.append(eid)

    rev = int(st.get("rev", 0)) + 1
    return _ok({"sel": selected, "drop": drop, "sp": {"rev": rev, "fsm": "SELECT_EVIDENCE"}})

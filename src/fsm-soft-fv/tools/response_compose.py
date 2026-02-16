def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


def _rationale(verdict):
    if verdict == "supported":
        return "Available evidence supports the claim."
    if verdict == "refuted":
        return "Available evidence contradicts the claim."
    if verdict == "mixed":
        return "Evidence is mixed and does not fully agree."
    return "Evidence is insufficient for a reliable judgment."


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")

    claims = args.get("claims")
    ver = args.get("ver")
    use = args.get("use")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}

    if not isinstance(claims, list) or not isinstance(ver, list):
        return _err("BAD_INPUT", "claims and ver must be lists")
    if use is None:
        use = []
    if not isinstance(use, list):
        use = []

    verdict_map = {}
    for item in ver:
        if isinstance(item, dict):
            verdict_map[item.get("id", "")] = item

    cite_map = {}
    for item in use:
        if not isinstance(item, dict):
            continue
        cid = item.get("for", "")
        eid = item.get("eid")
        if cid and eid:
            cite_map.setdefault(cid, []).append(eid)

    out = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        cid = claim.get("id", "")
        vv = verdict_map.get(cid)
        if not vv:
            out.append(
                {
                    "id": cid,
                    "ver": "insufficient",
                    "conf": "low",
                    "r": _rationale("insufficient"),
                    "cite": [],
                }
            )
            continue

        verdict = vv.get("v", "insufficient")
        conf = vv.get("conf", "low")
        out.append(
            {
                "id": cid,
                "ver": verdict,
                "conf": conf,
                "r": _rationale(verdict)[:200],
                "cite": cite_map.get(cid, [])[:2],
            }
        )

    rev = int(st.get("rev", 0)) + 1
    return _ok({"out": out, "sp": {"rev": rev, "fsm": "OUTPUT"}})

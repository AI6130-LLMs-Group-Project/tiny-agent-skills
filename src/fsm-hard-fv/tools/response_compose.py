### Tool to compose responses based on claims and verdicts

def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


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
    for v in ver:
        if isinstance(v, dict):
            verdict_map[v.get("id", "")] = v

    cite_map = {}
    for u in use:
        if not isinstance(u, dict):
            continue
        cid = u.get("for", "")
        eid = u.get("eid")
        if cid and eid:
            cite_map.setdefault(cid, []).append(eid)

    out = []
    for c in claims:
        if not isinstance(c, dict):
            continue
        cid = c.get("id", "")
        vv = verdict_map.get(cid)
        if not vv:
            out.append(
                {
                    "id": cid,
                    "ver": "insufficient",
                    "conf": "low",
                    "r": "Evidence is insufficient for a reliable judgment.",
                    "cite": [],
                }
            )
            continue
        v = vv.get("v", "insufficient")
        conf = vv.get("conf", "low")
        if v == "supported":
            r = "Available evidence supports the claim."
        elif v == "refuted":
            r = "Available evidence contradicts the claim."
        elif v == "mixed":
            r = "Evidence is mixed and does not fully agree."
        else:
            r = "Evidence is insufficient for a reliable judgment."
        out.append({"id": cid, "ver": v, "conf": conf, "r": r[:200], "cite": cite_map.get(cid, [])[:2]})

    rev = int(st.get("rev", 0)) + 1
    return _ok({"out": out, "sp": {"rev": rev, "fsm": "OUTPUT"}})

### This tool composes tool requests based on provided plans and state

def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "tools"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")
    plans = args.get("plans")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}
    if not isinstance(plans, list) or not plans:
        return _err("NO_PLANS", "plans is empty")

    trs = []
    t_index = 1
    for p in plans:
        if not isinstance(p, dict):
            continue
        pid = p.get("id", "s1")
        lim = p.get("lim", 3)
        queries = p.get("q", [])
        if not isinstance(queries, list):
            continue
        for q in queries:
            if not isinstance(q, str) or not q.strip():
                continue
            trs.append(
                {
                    "id": f"t{t_index}",
                    "tool": "search",
                    "args": {"q": q.strip(), "lim": lim, "src": "wiki"},
                    "for": pid,
                }
            )
            t_index += 1

    if not trs:
        return _err("NO_QUERIES", "no valid queries")
    rev = int(st.get("rev", 0)) + 1
    return _ok({"tr": trs, "sp": {"rev": rev, "fsm": "RETRIEVAL"}})

### This tool decomposes a complex claim into atomic sub-claims

import re


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


def _split_atomic(nc):
    text = nc.strip().rstrip(".")
    parts = re.split(r"\s+(?:and|or)\s+", text, flags=re.IGNORECASE)
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip(" ,;")
        if not p:
            continue
        if p[-1] not in ".!?":
            p += "."
        out.append(p[:200])
    return out


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")
    nc = args.get("nc")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}
    if not isinstance(nc, str) or len(nc.strip()) < 3:
        return _err("BAD_CLAIM", "nc must be non-empty string")

    parts = _split_atomic(nc)
    if len(parts) < 2:
        return _err("NOT_MULTI", "claim is not decomposable")

    subs = [{"id": f"s{i+1}", "c": p} for i, p in enumerate(parts)]
    rev = int(st.get("rev", 0)) + 1
    return _ok({"subs": subs, "sp": {"rev": rev, "fsm": "PARSE_CLAIM"}})

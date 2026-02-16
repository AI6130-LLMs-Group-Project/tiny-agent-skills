import re


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


def _split_atomic(text):
    base = text.strip().rstrip(".")
    parts = re.split(r"\s+(?:and|or)\s+", base, flags=re.IGNORECASE)
    out = []
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip(" ,;")
        if not part:
            continue
        if part[-1] not in ".!?":
            part += "."
        out.append(part[:200])
    return out


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")

    normalized = args.get("nc")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}
    if not isinstance(normalized, str) or len(normalized.strip()) < 3:
        return _err("BAD_CLAIM", "nc must be non-empty string")

    parts = _split_atomic(normalized)
    if len(parts) < 2:
        return _err("NOT_MULTI", "claim is not decomposable")

    subs = [{"id": f"s{i + 1}", "c": text} for i, text in enumerate(parts)]
    rev = int(st.get("rev", 0)) + 1
    return _ok({"subs": subs, "sp": {"rev": rev, "fsm": "PARSE_CLAIM"}})

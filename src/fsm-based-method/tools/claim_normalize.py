### This tool normalizes a claim so that we does not have to rely on that small LLM
# still, following a minimal naming of json fields

import re


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


def _clean_text(text):
    text = text.strip().strip("\"'`")
    text = re.sub(r"\s+", " ", text)
    return text


def _to_statement(text):
    out = text
    if out.endswith("?"):
        out = out[:-1].strip()
    if out and out[-1] not in ".!?":
        out += "."
    return out


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")
    c = args.get("c")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}
    if not isinstance(c, str):
        return _err("BAD_CLAIM", "c must be string")
    c = _clean_text(c)
    if len(c) < 3:
        return _err("EMPTY_CLAIM", "claim too short")
    if not re.search(r"[A-Za-z0-9]", c):
        return _err("NON_TEXT", "claim has no alnum chars")

    lowered = c.lower()
    ct = "atomic"
    if c.endswith("?"):
        ct = "question"
    elif " and " in lowered or " or " in lowered or ";" in c:
        ct = "multi"
    sd = ct == "multi"
    nc = _to_statement(c)

    rev = int(st.get("rev", 0)) + 1
    return _ok(
        {
            "nc": nc[:240],
            "ct": ct,
            "sd": sd,
            "sp": {"rev": rev, "fsm": "PARSE_CLAIM"},
        }
    )

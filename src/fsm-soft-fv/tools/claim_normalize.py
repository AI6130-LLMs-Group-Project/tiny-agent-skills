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

    claim = args.get("c")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}
    if not isinstance(claim, str):
        return _err("BAD_CLAIM", "c must be string")

    claim = _clean_text(claim)
    if len(claim) < 3:
        return _err("EMPTY_CLAIM", "claim too short")
    if not re.search(r"[A-Za-z0-9]", claim):
        return _err("NON_TEXT", "claim has no alnum chars")

    lowered = claim.lower()
    claim_type = "atomic"
    if claim.endswith("?"):
        claim_type = "question"
    elif " and " in lowered or " or " in lowered or ";" in claim:
        claim_type = "multi"

    should_decompose = claim_type == "multi"
    normalized = _to_statement(claim)
    rev = int(st.get("rev", 0)) + 1

    return _ok(
        {
            "nc": normalized[:240],
            "ct": claim_type,
            "sd": should_decompose,
            "sp": {"rev": rev, "fsm": "PARSE_CLAIM"},
        }
    )

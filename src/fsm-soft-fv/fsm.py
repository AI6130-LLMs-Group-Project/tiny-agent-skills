STATES = [
    "PARSE_CLAIM",
    "RETRIEVAL",
    "SELECT_EVIDENCE",
    "NLI_VERIFY",
    "DECIDE",
    "OUTPUT",
]


DEFAULT_NEXT = {
    "PARSE_CLAIM": "RETRIEVAL",
    "RETRIEVAL": "SELECT_EVIDENCE",
    "SELECT_EVIDENCE": "NLI_VERIFY",
    "NLI_VERIFY": "DECIDE",
    "DECIDE": "OUTPUT",
    "OUTPUT": "OUTPUT",
}


BACK_NEXT = {
    "SELECT_EVIDENCE": "RETRIEVAL",
}


def is_valid_state(name: str) -> bool:
    return name in STATES


def next_state(current: str, status: str) -> str:
    if status == "retry":
        return current
    if status == "back":
        return BACK_NEXT.get(current, current)
    if status == "error":
        return "OUTPUT"
    return DEFAULT_NEXT.get(current, "OUTPUT")

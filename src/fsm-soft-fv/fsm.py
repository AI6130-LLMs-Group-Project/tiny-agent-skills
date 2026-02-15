STATES = [
    "PARSE_CLAIM",
    "RETRIEVAL",
    "SELECT_EVIDENCE",
    "NLI_VERIFY",
    "DECIDE",
    "OUTPUT",
]


def is_valid_state(name: str) -> bool:
    return name in STATES

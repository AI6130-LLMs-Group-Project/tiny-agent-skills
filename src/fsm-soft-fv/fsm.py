TASK_STATES = {
    "fever": [
        "PARSE_CLAIM",
        "RETRIEVAL",
        "SELECT_EVIDENCE",
        "NLI_VERIFY",
        "DECIDE",
        "OUTPUT",
    ],
    "gsm8k": [
        "PARSE_PROBLEM",
        "PLAN_SOLUTION",
        "EXECUTE_SOLUTION",
        "VERIFY_SOLUTION",
        "OUTPUT",
    ],
}


TASK_DEFAULT_NEXT = {
    "fever": {
        "PARSE_CLAIM": "RETRIEVAL",
        "RETRIEVAL": "SELECT_EVIDENCE",
        "SELECT_EVIDENCE": "NLI_VERIFY",
        "NLI_VERIFY": "DECIDE",
        "DECIDE": "OUTPUT",
        "OUTPUT": "OUTPUT",
    },
    "gsm8k": {
        "PARSE_PROBLEM": "PLAN_SOLUTION",
        "PLAN_SOLUTION": "EXECUTE_SOLUTION",
        "EXECUTE_SOLUTION": "VERIFY_SOLUTION",
        "VERIFY_SOLUTION": "OUTPUT",
        "OUTPUT": "OUTPUT",
    },
}


TASK_BACK_NEXT = {
    "fever": {
        "SELECT_EVIDENCE": "RETRIEVAL",
    },
    "gsm8k": {},
}


def _normalize_task(task: str) -> str:
    task_name = (task or "fever").strip().lower()
    if task_name in {"fact", "fact_verification", "fact-verification"}:
        return "fever"
    if task_name in {"gsm", "math", "gsm8k"}:
        return "gsm8k"
    return "fever"


def is_valid_state(name: str, task: str = "fever") -> bool:
    task_name = _normalize_task(task)
    return name in TASK_STATES.get(task_name, TASK_STATES["fever"])


def next_state(current: str, status: str, task: str = "fever") -> str:
    task_name = _normalize_task(task)
    default_next = TASK_DEFAULT_NEXT.get(task_name, TASK_DEFAULT_NEXT["fever"])
    back_next = TASK_BACK_NEXT.get(task_name, TASK_BACK_NEXT["fever"])
    final_state = "OUTPUT"
    if status == "retry":
        return current
    if status == "back":
        return back_next.get(current, current)
    if status == "error":
        return final_state
    return default_next.get(current, final_state)

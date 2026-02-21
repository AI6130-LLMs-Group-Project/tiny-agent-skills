from __future__ import annotations

from pathlib import Path


_BASE = Path(__file__).resolve().parents[1]
_SKILLS_DIR = _BASE / "skills"
_SUBSKILLS_DIR = _SKILLS_DIR / "subskills"
_TOOLS_DIR = _BASE / "tools"


SKILLS = {
    "fsm_controller": {
        "id": "fsm_controller",
        "path": str(_SKILLS_DIR / "fsm-controller.md"),
    },
    "fsm_fact_verification": {
        "id": "fsm_fact_verification",
        "path": str(_SKILLS_DIR / "fsm-fact-verification.md"),
    },
    "fsm_essay_writer": {
        "id": "fsm_essay_writer",
        "path": str(_SKILLS_DIR / "fsm-essay-writer.md"),
    },
    "fsm_math_solver": {
        "id": "fsm_math_solver",
        "path": str(_SKILLS_DIR / "fsm-math-solver.md"),
    },
}


SUBSKILLS = {
    "parse_claim": {
        "id": "parse_claim",
        "path": str(_SUBSKILLS_DIR / "parse-claim.md"),
    },
    "retrieval_planning": {
        "id": "retrieval_planning",
        "path": str(_SUBSKILLS_DIR / "retrieval-planning.md"),
    },
    "retrieval_execution": {
        "id": "retrieval_execution",
        "path": str(_SUBSKILLS_DIR / "retrieval-execution.md"),
    },
    "evidence_selection": {
        "id": "evidence_selection",
        "path": str(_SUBSKILLS_DIR / "evidence-selection.md"),
    },
    "nli_verification": {
        "id": "nli_verification",
        "path": str(_SUBSKILLS_DIR / "nli-verification.md"),
    },
    "verdict_decision": {
        "id": "verdict_decision",
        "path": str(_SUBSKILLS_DIR / "verdict-decision.md"),
    },
    "response_output": {
        "id": "response_output",
        "path": str(_SUBSKILLS_DIR / "response-output.md"),
    },
    # Compatibility aliases for the originally tracked filenames.
    "retrieval": {
        "id": "retrieval",
        "path": str(_SUBSKILLS_DIR / "retrieval.md"),
    },
    "select_evidence": {
        "id": "select_evidence",
        "path": str(_SUBSKILLS_DIR / "select-evidence.md"),
    },
    "nli_verify": {
        "id": "nli_verify",
        "path": str(_SUBSKILLS_DIR / "nli-verify.md"),
    },
    "decide": {
        "id": "decide",
        "path": str(_SUBSKILLS_DIR / "decide.md"),
    },
    "output": {
        "id": "output",
        "path": str(_SUBSKILLS_DIR / "output.md"),
    },
    "tool_use_policy": {
        "id": "tool_use_policy",
        "path": str(_SUBSKILLS_DIR / "tool-use-policy.md"),
    },
    "parse_math_problem": {
        "id": "parse_math_problem",
        "path": str(_SUBSKILLS_DIR / "parse-math-problem.md"),
    },
    "plan_math_solution": {
        "id": "plan_math_solution",
        "path": str(_SUBSKILLS_DIR / "plan-math-solution.md"),
    },
    "execute_math_solution": {
        "id": "execute_math_solution",
        "path": str(_SUBSKILLS_DIR / "execute-math-solution.md"),
    },
    "verify_math_solution": {
        "id": "verify_math_solution",
        "path": str(_SUBSKILLS_DIR / "verify-math-solution.md"),
    },
    "math_output": {
        "id": "math_output",
        "path": str(_SUBSKILLS_DIR / "math-output.md"),
    },
    "math_tool_use": {
        "id": "math_tool_use",
        "path": str(_SUBSKILLS_DIR / "math-tool-use.md"),
    },
}


TOOLS = {
    "search": {
        "id": "search",
        "path": str(_TOOLS_DIR / "search.py"),
    },
    "web_search": {
        "id": "web_search",
        "path": str(_TOOLS_DIR / "web_search.py"),
    },
    "page_fetch": {
        "id": "page_fetch",
        "path": str(_TOOLS_DIR / "page_fetch.py"),
    },
    "sentence_extract": {
        "id": "sentence_extract",
        "path": str(_TOOLS_DIR / "sentence_extract.py"),
    },
    "math_eval": {
        "id": "math_eval",
        "path": str(_TOOLS_DIR / "math_eval.py"),
    },
    "math_check": {
        "id": "math_check",
        "path": str(_TOOLS_DIR / "math_check.py"),
    },
}


STATE_TOOL_SCOPE = {
    "fever": {
        "PARSE_CLAIM": [],
        "RETRIEVAL": ["search", "web_search", "page_fetch", "sentence_extract"],
        "SELECT_EVIDENCE": [],
        "NLI_VERIFY": [],
        "DECIDE": [],
        "OUTPUT": [],
    },
    "gsm8k": {
        "PARSE_PROBLEM": [],
        "PLAN_SOLUTION": [],
        "EXECUTE_SOLUTION": ["math_eval", "math_check"],
        "VERIFY_SOLUTION": [],
        "OUTPUT": [],
    },
}


def list_skills():
    return list(SKILLS.values())


def list_subskills():
    return list(SUBSKILLS.values())


def list_tools():
    return list(TOOLS.values())


def tools_for_state(state, task: str = "fever"):
    task_name = (task or "fever").strip().lower()
    if task_name not in STATE_TOOL_SCOPE:
        task_name = "fever"
    return list(STATE_TOOL_SCOPE.get(task_name, {}).get(state, []))

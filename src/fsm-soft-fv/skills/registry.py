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
    "kb_lookup": {
        "id": "kb_lookup",
        "path": str(_TOOLS_DIR / "kb_lookup.py"),
    },
    "page_fetch": {
        "id": "page_fetch",
        "path": str(_TOOLS_DIR / "page_fetch.py"),
    },
    "sentence_extract": {
        "id": "sentence_extract",
        "path": str(_TOOLS_DIR / "sentence_extract.py"),
    },
}


STATE_TOOL_SCOPE = {
    "PARSE_CLAIM": [],
    "RETRIEVAL": ["search", "kb_lookup", "web_search", "page_fetch", "sentence_extract"],
    "SELECT_EVIDENCE": [],
    "NLI_VERIFY": [],
    "DECIDE": [],
    "OUTPUT": [],
}


def list_skills():
    return list(SKILLS.values())


def list_subskills():
    return list(SUBSKILLS.values())


def list_tools():
    return list(TOOLS.values())


def tools_for_state(state):
    return list(STATE_TOOL_SCOPE.get(state, []))

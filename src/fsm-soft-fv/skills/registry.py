from __future__ import annotations

from pathlib import Path
from typing import Dict, List


_ROOT = Path(__file__).resolve().parents[2]
_SKILLS_DIR = _ROOT / "fsm-soft-fv" / "skills"
_SUBSKILLS_DIR = _SKILLS_DIR / "subskills"
_TOOLS_DIR = _ROOT / "fsm-soft-fv" / "tools"


SKILLS = {
    "fsm_controller": {
        "id": "fsm_controller",
        "path": str(_SKILLS_DIR / "fsm-controller.md"),
        "subskills": [
            "parse_claim",
            "retrieval",
            "select_evidence",
            "nli_verify",
            "decide",
            "output",
            "tool_use_policy",
        ],
    }
}


SUBSKILLS = {
    "parse_claim": {"id": "parse_claim", "path": str(_SUBSKILLS_DIR / "parse-claim.md")},
    "retrieval": {"id": "retrieval", "path": str(_SUBSKILLS_DIR / "retrieval.md")},
    "select_evidence": {"id": "select_evidence", "path": str(_SUBSKILLS_DIR / "select-evidence.md")},
    "nli_verify": {"id": "nli_verify", "path": str(_SUBSKILLS_DIR / "nli-verify.md")},
    "decide": {"id": "decide", "path": str(_SUBSKILLS_DIR / "decide.md")},
    "output": {"id": "output", "path": str(_SUBSKILLS_DIR / "output.md")},
    "tool_use_policy": {"id": "tool_use_policy", "path": str(_SUBSKILLS_DIR / "tool-use-policy.md")},
}


TOOLS = {
    "search": {"id": "search", "path": str(_TOOLS_DIR / "search.py")},
    "web_search": {"id": "web_search", "path": str(_TOOLS_DIR / "web_search.py")},
    "kb_lookup": {"id": "kb_lookup", "path": str(_TOOLS_DIR / "kb_lookup.py")},
    "page_fetch": {"id": "page_fetch", "path": str(_TOOLS_DIR / "page_fetch.py")},
}


STATE_TOOL_SCOPE: Dict[str, List[str]] = {
    "PARSE_CLAIM": [],
    "RETRIEVAL": ["search", "kb_lookup", "web_search", "page_fetch"],
    "SELECT_EVIDENCE": [],
    "NLI_VERIFY": [],
    "DECIDE": [],
    "OUTPUT": [],
}


TOOL_HINTS: Dict[str, str] = {
    "search": "Wikipedia/DDG retrieval. Good precision for encyclopedic facts and cheap.",
    "kb_lookup": "Local cumulative evidence lookup. Cheap but can be stale for new claims.",
    "web_search": "External paid search. Better freshness and breadth, but higher cost.",
    "page_fetch": "Fetch raw page text when search snippets are not enough.",
}


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_controller_prompt() -> str:
    root = _read(SKILLS["fsm_controller"]["path"])
    blocks = [root]
    for sid in SKILLS["fsm_controller"].get("subskills", []):
        meta = SUBSKILLS.get(sid)
        if not meta:
            continue
        blocks.append("\n\n# Subskill: " + sid + "\n" + _read(meta["path"]))
    return "\n".join(blocks)

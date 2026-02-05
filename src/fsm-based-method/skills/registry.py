from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2]
_SKILLS_DIR = _ROOT / "fsm-based-method" / "skills"
_TOOLS_DIR = _ROOT / "fsm-based-method" / "tools"


SKILLS = {
    "claim_normalizer": {
        "id": "claim_normalizer",
        "path": str(_SKILLS_DIR / "claim-normalizer.md"),
    },
    "claim_decomposer": {
        "id": "claim_decomposer",
        "path": str(_SKILLS_DIR / "claim-decomposer.md"),
    },
    "evidence_query_planner": {
        "id": "evidence_query_planner",
        "path": str(_SKILLS_DIR / "evidence-query-planner.md"),
    },
    "evidence_filter": {
        "id": "evidence_filter",
        "path": str(_SKILLS_DIR / "evidence-filter.md"),
    },
    "evidence_stance_scorer": {
        "id": "evidence_stance_scorer",
        "path": str(_SKILLS_DIR / "evidence-stance-scorer.md"),
    },
    "verdict_aggregator": {
        "id": "verdict_aggregator",
        "path": str(_SKILLS_DIR / "verdict-aggregator.md"),
    },
    "response_composer": {
        "id": "response_composer",
        "path": str(_SKILLS_DIR / "response-composer.md"),
    },
}


TOOLS = {
    "search": {
        "id": "search",
        "module": "fsm-based-method.tools.search",
        "path": str(_TOOLS_DIR / "search.py"),
    },
    "web_search": {
        "id": "web_search",
        "module": "fsm-based-method.tools.web_search",
        "path": str(_TOOLS_DIR / "web_search.py"),
    },
    "page_fetch": {
        "id": "page_fetch",
        "module": "fsm-based-method.tools.page_fetch",
        "path": str(_TOOLS_DIR / "page_fetch.py"),
    },
    "sentence_extract": {
        "id": "sentence_extract",
        "module": "fsm-based-method.tools.sentence_extract",
        "path": str(_TOOLS_DIR / "sentence_extract.py"),
    },
    "kb_lookup": {
        "id": "kb_lookup",
        "module": "fsm-based-method.tools.kb_lookup",
        "path": str(_TOOLS_DIR / "kb_lookup.py"),
    },
    "claim_normalize": {
        "id": "claim_normalize",
        "module": "fsm-based-method.tools.claim_normalize",
        "path": str(_TOOLS_DIR / "claim_normalize.py"),
    },
    "claim_decompose": {
        "id": "claim_decompose",
        "module": "fsm-based-method.tools.claim_decompose",
        "path": str(_TOOLS_DIR / "claim_decompose.py"),
    },
    "nli_score": {
        "id": "nli_score",
        "module": "fsm-based-method.tools.nli_score",
        "path": str(_TOOLS_DIR / "nli_score.py"),
    },
    "response_compose": {
        "id": "response_compose",
        "module": "fsm-based-method.tools.response_compose",
        "path": str(_TOOLS_DIR / "response_compose.py"),
    },
    "verdict_aggregate": {
        "id": "verdict_aggregate",
        "module": "fsm-based-method.tools.verdict_aggregate",
        "path": str(_TOOLS_DIR / "verdict_aggregate.py"),
    },
    "evidence_query_plan": {
        "id": "evidence_query_plan",
        "module": "fsm-based-method.tools.evidence_query_plan",
        "path": str(_TOOLS_DIR / "evidence_query_plan.py"),
    },
}


def list_skills():
    return list(SKILLS.values())


def list_tools():
    return list(TOOLS.values())

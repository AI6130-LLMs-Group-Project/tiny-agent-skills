### Define allowed skills and tools for each FSM state (scoping)

# FSM State > skills (added at least one skill per state)
SKILL_SCOPE = {
    "PARSE_CLAIM": [
        "claim_normalizer",
        "claim_decomposer",
        "evidence_query_planner",
    ],
    "RETRIEVAL": [
        "tool_request_composer",
    ],
    "SELECT_EVIDENCE": [
        "evidence_filter",
    ],
    "NLI_VERIFY": [
        "evidence_stance_scorer",
    ],
    "DECIDE": [
        "verdict_aggregator",
    ],
    "OUTPUT": [
        "response_composer",
    ],
}

# FSM State > tools
TOOL_SCOPE = {
    "PARSE_CLAIM": [
        "claim_normalize",
        "claim_decompose",
    ],
    "RETRIEVAL": [
        "tool_request_compose",
        "search",
        "web_search",
        "kb_lookup",
        "page_fetch",
        "sentence_extract",
    ],
    "SELECT_EVIDENCE": [],
    "NLI_VERIFY": [
        "nli_score",
    ],
    "DECIDE": [
        "verdict_aggregate",
    ],
    "OUTPUT": [
        "response_compose",
    ],
}


def allowed_skills(state: str):
    return SKILL_SCOPE.get(state, [])


def allowed_tools(state: str):
    return TOOL_SCOPE.get(state, [])


def allow_skill(state: str, skill_id: str) -> bool:
    return skill_id in SKILL_SCOPE.get(state, [])


def allow_tool(state: str, tool_id: str) -> bool:
    return tool_id in TOOL_SCOPE.get(state, [])

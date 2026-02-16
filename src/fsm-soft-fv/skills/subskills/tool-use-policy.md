# Tool Use Policy Subskill

## Allowed Tool Scope by State
- `PARSE_CLAIM`: no tool (LLM reasoning)
- `RETRIEVAL`: `search`, `kb_lookup`, `web_search`, `page_fetch`, `sentence_extract`
- `SELECT_EVIDENCE`: no tool (LLM reasoning)
- `NLI_VERIFY`: no tool (LLM reasoning)
- `DECIDE`: no tool (LLM reasoning)
- `OUTPUT`: no tool (LLM reasoning)

## Policy
1. Use tools only to collect evidence candidates.
2. Do not use tools to decide stance/verdict.
3. If planner output violates scope, ignore it and use orchestrator defaults.

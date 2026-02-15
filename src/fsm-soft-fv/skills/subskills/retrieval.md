## Retrieval State

Goal:
- gather candidate evidence for each claim

Tool guidance:
- `search`: good precision for encyclopedia-style claims
- `kb_lookup`: cheap but cumulative/stale for new claims
- `web_search`: fresher and broader, but paid API usage
- `page_fetch`: fetch full text when snippets are insufficient

Use `write.evidence` to add cleaned snippets after analyzing tool outputs.
Tool calls must provide concrete query args, e.g. `{"q":"...","lim":4,"src":"wiki"}` for `search`.

Exit condition:
- enough evidence collected for at least one claim, then `SELECT_EVIDENCE`
- otherwise retry retrieval

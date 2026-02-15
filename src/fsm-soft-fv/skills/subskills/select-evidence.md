## Select Evidence State

Goal:
- select the most relevant evidence for each claim

Do this with LLM reasoning in `write.selected`.
Use evidence ids already in memory.

Exit condition:
- `selected` non-empty, then move to `NLI_VERIFY`
- if empty, move back to `RETRIEVAL`

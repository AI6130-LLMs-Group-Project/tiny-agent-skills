# Retrieval Execution Subskill

## Goal
Pick a retrieval tool for each query and collect evidence rows.

## Allowed tools
- `search` (wiki/default)
- `kb_lookup`
- `web_search` (if key/provider exists)

## Procedure
1. For each query, choose one allowed tool.
2. Execute tool with safe args (`q`, `lim`, optional `src`).
3. If empty results, try next fallback tool.
4. Convert rows to canonical evidence entries.

## Rule
No result is better than fake result. Keep it honest.

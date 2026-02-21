# Retrieval Execution Subskill

## Goal
Pick a retrieval tool for each query and collect evidence rows.

## Allowed tools
- `search` (wiki/default)
- `web_search` (if key/provider exists)
- `page_fetch`
- `sentence_extract`

## Procedure
1. For each query, choose one allowed tool.
2. Execute tool with safe args (`q`, `lim`, optional `src`).
3. If search rows include URLs, optionally use `page_fetch` + `sentence_extract` to extract targeted snippets.
4. Prefer `TOP_N` as sentence extraction target and respect `WIKI_FETCH_LIMIT` for page expansion budget.
5. If empty results, try next fallback tool.
6. Convert rows to canonical evidence entries.

## Rule
No result is better than fake result. Keep it honest.

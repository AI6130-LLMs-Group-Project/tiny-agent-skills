# Retrieval Subskill

1. Build query plans with `evidence_query_plan`.
2. For each query, pick retrieval tool (`search`, `kb_lookup`, `web_search`) and execute.
3. Keep rows with lexical overlap and convert to canonical evidence items.

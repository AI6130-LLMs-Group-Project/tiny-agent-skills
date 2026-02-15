## Tool Use Policy

Rules:
1. Use tools only for retrieval or source text access.
2. Do not use tools for claim parsing, evidence ranking, NLI, verdict aggregation, or response writing.
3. At most one tool call per turn.
4. If a retrieval tool fails, retry with adjusted args or a different retrieval tool.
5. Keep expensive retrieval (`web_search`) as fallback after cheaper options.

# Evidence Query Planner Skill

## Purpose
Produce minimal search/retrieval query plans for each subclaim.

## When to use (FSM state)
- `PARSE_CLAIM` (single or decomposed claims)

## Inputs schema
```json
{
  "claims": [ { "id": "s1", "c": "string" } ],
  "st": { "sid": "string", "rev": "int", "fsm": "string" },
  "hints": [ "string" ] | null
}
```

## Outputs schema
```json
{
  "s": "ok|error|retry",
  "d": {
    "plans": [
      {
        "id": "s1",
        "q": [ "string" ],     // short queries
        "src": [ "wiki|web|news|kb" ],
        "lim": "int"           // max results per query
      }
    ],
    "sp": { "rev": "int", "fsm": "string" }
  },
  "e": { "code": "string", "msg": "string" } | null,
  "rb": "none|state"
}
```

## Allowed tools
- none (no direct tool calls); executor may use `tool.search`, `tool.web_search`, or `tool.kb_lookup` based on `src`

## Algorithm/logic steps
1. For each claim, extract 2-4 key terms and any named entities.
2. Form 1-2 concise queries per claim, <= 6 tokens each.
3. Select sources: use `wiki` or `kb` for encyclopedic facts, `news` for recent claims, else `web`.
4. Set `lim` between 3 and 5 to limit token usage.
5. Set `sp.fsm` to `RETRIEVAL` and increment `sp.rev` by 1.

## Constraints
- Queries must be deterministic for identical inputs.
- Do not include user context unless it changes factual meaning.
- Use lowercase unless proper nouns are required.

## Failure modes
- `NO_CLAIMS`: empty list.
- `QUERY_TOO_LONG`: any query > 6 tokens.
- Rollback: `rb=state`.

## Example I/O
Input
```json
{ "claims": [ { "id": "s1", "c": "NASA landed on the Moon in 1969." } ], "st": { "sid": "A1", "rev": 5, "fsm": "PARSE_CLAIM" }, "hints": null }
```
Output
```json
{ "s": "ok", "d": { "plans": [ { "id": "s1", "q": [ "NASA Moon landing 1969" ], "src": [ "wiki", "web" ], "lim": 4 } ], "sp": { "rev": 6, "fsm": "RETRIEVAL" } }, "e": null, "rb": "none" }
```



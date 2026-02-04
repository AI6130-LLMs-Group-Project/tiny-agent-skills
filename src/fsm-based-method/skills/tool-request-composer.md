# Tool Request Composer Skill

## Purpose
Translate query plans into minimal tool call requests for the executor.

## When to use (FSM state)
- `RETRIEVAL`

## Inputs schema
```json
{
  "plans": [ { "id": "s1", "q": [ "string" ], "src": [ "wiki|web|news|kb" ], "lim": "int" } ],
  "st": { "sid": "string", "rev": "int", "fsm": "string" }
}
```

## Outputs schema
```json
{
  "s": "ok|error|retry",
  "d": {
    "tr": [
      { "id": "t1", "tool": "search|kb_lookup", "args": { "q": "string", "lim": "int", "src": "wiki|web|news|kb" }, "for": "s1" }
    ],
    "sp": { "rev": "int", "fsm": "string" }
  },
  "e": { "code": "string", "msg": "string" } | null,
  "rb": "none|state|tools"
}
```

## Allowed tools
- `tool.tool_request_compose` (preferred deterministic path)
- `tool.search`
- `tool.web_search`
- `tool.kb_lookup`
- `tool.page_fetch`
- `tool.sentence_extract`

## Algorithm/logic steps
1. For each query, choose `kb_lookup` only if `src` is exactly `["kb"]`.
2. Otherwise choose `search` and set `args.src` to the first non-`kb` entry, preferring `wiki` over `web` over `news`.
3. If `search` fails due to rate limits, executor may reissue with `web_search` using the same query and limit.
4. Assign `t1`, `t2`, ... deterministically by plan order.
5. Set `sp.fsm` to `RETRIEVAL` and increment `sp.rev` by 1.

## Constraints
- Do not merge queries.
- `args.q` must match the planned query exactly.
- `args.src` is required for `search` and must be one of `wiki|web|news|kb`.
- If no plans, return `s=error`.

## Failure modes
- `NO_PLANS`: empty input.
- `BAD_SRC`: unsupported source value.
- Rollback: `rb=tools`.

## Example I/O
Input
```json
{ "plans": [ { "id": "s1", "q": [ "NASA Moon landing 1969" ], "src": [ "wiki", "web" ], "lim": 4 } ], "st": { "sid": "A1", "rev": 6, "fsm": "RETRIEVAL" } }
```
Output
```json
{ "s": "ok", "d": { "tr": [ { "id": "t1", "tool": "search", "args": { "q": "NASA Moon landing 1969", "lim": 4, "src": "wiki" }, "for": "s1" } ], "sp": { "rev": 7, "fsm": "RETRIEVAL" } }, "e": null, "rb": "none" }
```



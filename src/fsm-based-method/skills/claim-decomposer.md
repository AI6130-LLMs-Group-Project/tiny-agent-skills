# Claim Decomposer Skill

## Purpose
Split a multi-fact claim into minimal atomic subclaims for independent verification.

## When to use (FSM state)
- `PARSE_CLAIM` when `sd=true`

## Inputs schema
```json
{
  "nc": "string",       // normalized claim
  "lang": "string",
  "st": { "sid": "string", "rev": "int", "fsm": "string" }
}
```

## Outputs schema
```json
{
  "s": "ok|error|retry",
  "d": {
    "subs": [ { "id": "s1", "c": "string" } ],
    "sp": { "rev": "int", "fsm": "string" }
  },
  "e": { "code": "string", "msg": "string" } | null,
  "rb": "none|state"
}
```

## Allowed tools
- `tool.claim_decompose` (preferred deterministic path)

## Algorithm/logic steps
1. Identify independent propositions linked by coordination or multiple clauses.
2. Split into minimal atomic claims that can be verified separately.
3. Keep shared context in each subclaim if needed for meaning.
4. Assign stable ids `s1`, `s2`, ... in order of appearance.
5. Set `sp.fsm` to `PARSE_CLAIM` and increment `sp.rev` by 1.

## Constraints
- Do not split causal or conditional statements into parts that change meaning.
- Each subclaim <= 200 characters.
- At least 2 subclaims required; otherwise return `s=error`.

## Failure modes
- `NOT_MULTI`: claim is not decomposable.
- `OVER_SPLIT`: split would lose meaning.
- Rollback: `rb=state`.

## Example I/O
Input
```json
{ "nc": "Paris is in France and the Eiffel Tower is in Paris.", "lang": "en", "st": { "sid": "A1", "rev": 4, "fsm": "PARSE_CLAIM" } }
```
Output
```json
{ "s": "ok", "d": { "subs": [ { "id": "s1", "c": "Paris is in France." }, { "id": "s2", "c": "The Eiffel Tower is in Paris." } ], "sp": { "rev": 5, "fsm": "PARSE_CLAIM" } }, "e": null, "rb": "none" }
```



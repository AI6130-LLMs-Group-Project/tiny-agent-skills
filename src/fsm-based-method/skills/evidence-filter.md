# Evidence Filter Skill

## Purpose
Select the most relevant compressed sentence-level evidence for each claim.

## When to use (FSM state)
- `SELECT_EVIDENCE`

## Inputs schema
```json
{
  "claims": [ { "id": "s1", "c": "string" } ],
  "ev": [
    { "eid": "e1", "for": "s1", "s": "string", "src": "string", "d": "YYYY-MM-DD|null", "cred": "low|med|high" }
  ],
  "st": { "sid": "string", "rev": "int", "fsm": "string" }
}
```

## Outputs schema
```json
{
  "s": "ok|error|retry",
  "d": {
    "sel": [ { "eid": "e1", "for": "s1" } ],
    "drop": [ "eid" ],
    "sp": { "rev": "int", "fsm": "string" }
  },
  "e": { "code": "string", "msg": "string" } | null,
  "rb": "none|state"
}
```

## Allowed tools
- none (no direct tool calls)

## Algorithm/logic steps
1. For each claim, keep evidence with direct lexical or named-entity overlap.
2. Prefer `cred=high` when ties exist.
3. Keep at most 5 sentences per claim.
4. Output selected ids in input order; remaining go to `drop`.
5. Set `sp.fsm` to `SELECT_EVIDENCE` and increment `sp.rev` by 1.

## Constraints
- Never fabricate evidence; only select from `ev`.
- If no evidence matches any claim, return `s=retry`.

## Failure modes
- `NO_EVIDENCE`: empty `ev`.
- `NO_MATCH`: all evidence filtered out.
- Rollback: `rb=state`.

## Example I/O
Input
```json
{ "claims": [ { "id": "s1", "c": "NASA landed on the Moon in 1969." } ], "ev": [ { "eid": "e1", "for": "s1", "s": "Apollo 11 landed on the Moon in July 1969.", "src": "encyclopedia", "d": "1969-07-20", "cred": "high" } ], "st": { "sid": "A1", "rev": 8, "fsm": "SELECT_EVIDENCE" } }
```
Output
```json
{ "s": "ok", "d": { "sel": [ { "eid": "e1", "for": "s1" } ], "drop": [], "sp": { "rev": 9, "fsm": "SELECT_EVIDENCE" } }, "e": null, "rb": "none" }
```



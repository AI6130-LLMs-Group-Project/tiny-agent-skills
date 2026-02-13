# Verdict Aggregator Skill

## Purpose
Aggregate per-evidence stance scores into a verdict for each claim.

## When to use (FSM state)
- `DECIDE`

## Inputs schema
```json
{
  "claims": [ { "id": "s1", "c": "string" } ],
  "scores": [ { "eid": "e1", "for": "s1", "st": "support|refute|neutral", "conf": "low|med|high" } ],
  "st": { "sid": "string", "rev": "int", "fsm": "string" }
}
```

## Outputs schema
```json
{
  "s": "ok|error|retry",
  "d": {
    "ver": [ { "id": "s1", "v": "supported|refuted|mixed|insufficient", "conf": "low|med|high" } ],
    "sp": { "rev": "int", "fsm": "string" }
  },
  "e": { "code": "string", "msg": "string" } | null,
  "rb": "none|state"
}
```

## Allowed tools
- `tool.verdict_aggregate` (preferred deterministic path)

## Algorithm/logic steps
1. For each claim, count support vs refute at medium/high confidence.
2. If only support and at least one high, set `supported`.
3. If only refute and at least one high, set `refuted`.
4. If both support and refute, set `mixed`.
5. If only neutral/low, set `insufficient`.
6. Set `sp.fsm` to `DECIDE` and increment `sp.rev` by 1.

## Constraints
- Deterministic aggregation.
- Do not override claim wording.

## Failure modes
- `NO_SCORES`: empty input.
- Rollback: `rb=state`.

## Example I/O
Input
```json
{ "claims": [ { "id": "s1", "c": "NASA landed on the Moon in 1969." } ], "scores": [ { "eid": "e1", "for": "s1", "st": "support", "conf": "high" } ], "st": { "sid": "A1", "rev": 10, "fsm": "DECIDE" } }
```
Output
```json
{ "s": "ok", "d": { "ver": [ { "id": "s1", "v": "supported", "conf": "high" } ], "sp": { "rev": 11, "fsm": "DECIDE" } }, "e": null, "rb": "none" }
```



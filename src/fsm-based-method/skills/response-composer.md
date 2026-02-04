# Response Composer Skill

## Purpose
Compose a minimal, citation-ready response outline from verdicts and evidence ids.

## When to use (FSM state)
- `OUTPUT`

## Inputs schema
```json
{
  "claims": [ { "id": "s1", "c": "string" } ],
  "ver": [ { "id": "s1", "v": "supported|refuted|mixed|insufficient", "conf": "low|med|high" } ],
  "use": [ { "eid": "e1", "for": "s1" } ],
  "st": { "sid": "string", "rev": "int", "fsm": "string" }
}
```

## Outputs schema
```json
{
  "s": "ok|error|retry",
  "d": {
    "out": [
      {
        "id": "s1",
        "ver": "supported|refuted|mixed|insufficient",
        "conf": "low|med|high",
        "r": "string",        // short rationale
        "cite": [ "eid" ]
      }
    ],
    "sp": { "rev": "int", "fsm": "string" }
  },
  "e": { "code": "string", "msg": "string" } | null,
  "rb": "none|state"
}
```

## Allowed tools
- `tool.response_compose` (preferred deterministic path)

## Algorithm/logic steps
1. For each claim, copy verdict and confidence.
2. Write a one-sentence rationale using only claim + evidence sentence content.
3. Include 1-2 evidence ids in `cite`.
4. Set `sp.fsm` to `OUTPUT` and increment `sp.rev` by 1.

## Constraints
- Rationale <= 200 characters.
- No new facts; no source names beyond ids.
- If `v=insufficient`, rationale must say evidence is lacking.

## Failure modes
- `MISSING_VERDICT`: verdict missing for claim.
- Rollback: `rb=state`.

## Example I/O
Input
```json
{ "claims": [ { "id": "s1", "c": "NASA landed on the Moon in 1969." } ], "ver": [ { "id": "s1", "v": "supported", "conf": "high" } ], "use": [ { "eid": "e1", "for": "s1" } ], "st": { "sid": "A1", "rev": 11, "fsm": "OUTPUT" } }
```
Output
```json
{ "s": "ok", "d": { "out": [ { "id": "s1", "ver": "supported", "conf": "high", "r": "Evidence states Apollo 11 landed on the Moon in July 1969.", "cite": [ "e1" ] } ], "sp": { "rev": 12, "fsm": "OUTPUT" } }, "e": null, "rb": "none" }
```



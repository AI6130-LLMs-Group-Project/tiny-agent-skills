# Evidence Stance Scorer Skill

## Purpose
Score how each selected evidence sentence supports or refutes a claim.

## When to use (FSM state)
- `NLI_VERIFY`

## Inputs schema
```json
{
  "claims": [ { "id": "s1", "c": "string" } ],
  "sel": [ { "eid": "e1", "for": "s1", "s": "string", "cred": "low|med|high" } ],
  "st": { "sid": "string", "rev": "int", "fsm": "string" }
}
```

## Outputs schema
```json
{
  "s": "ok|error|retry",
  "d": {
    "scores": [
      { "eid": "e1", "for": "s1", "st": "support|refute|neutral", "conf": "low|med|high" }
    ],
    "sp": { "rev": "int", "fsm": "string" }
  },
  "e": { "code": "string", "msg": "string" } | null,
  "rb": "none|state"
}
```

## Allowed tools
- `tool.nli_score` (preferred deterministic path)

## Algorithm/logic steps
1. Compare claim with evidence sentence for direct agreement or contradiction.
2. If evidence is about a different entity or time, mark `neutral`.
3. Set `conf` based on evidence specificity and `cred`.
4. Preserve input order.
5. Set `sp.fsm` to `NLI_VERIFY` and increment `sp.rev` by 1.

## Constraints
- Deterministic mapping; no new facts.
- If evidence is ambiguous, choose `neutral` with low confidence.

## Failure modes
- `NO_SELECTED`: empty `sel`.
- Rollback: `rb=state`.

## Example I/O
Input
```json
{ "claims": [ { "id": "s1", "c": "NASA landed on the Moon in 1969." } ], "sel": [ { "eid": "e1", "for": "s1", "s": "Apollo 11 landed on the Moon in July 1969.", "cred": "high" } ], "st": { "sid": "A1", "rev": 9, "fsm": "NLI_VERIFY" } }
```
Output
```json
{ "s": "ok", "d": { "scores": [ { "eid": "e1", "for": "s1", "st": "support", "conf": "high" } ], "sp": { "rev": 10, "fsm": "NLI_VERIFY" } }, "e": null, "rb": "none" }
```



# FSM Transition Decider Skill

## Purpose
Select the next FSM state based on current status and errors.

## When to use (FSM state)
- `ANY_STATE` after a skill output is produced

## Inputs schema
```json
{
  "last": { "skill": "string", "s": "ok|error|retry", "e": { "code": "string" } | null },
  "st": { "sid": "string", "rev": "int", "fsm": "string" }
}
```

## Outputs schema
```json
{
  "s": "ok|error|retry",
  "d": { "next": "string", "sp": { "rev": "int", "fsm": "string" } },
  "e": { "code": "string", "msg": "string" } | null,
  "rb": "none|state"
}
```

## Allowed tools
- none (no direct tool calls)

## Algorithm/logic steps
1. If `last.s=ok`, advance to the canonical next state in the pipeline.
2. If `last.s=retry`, keep same state for reattempt.
3. If `last.s=error`, move to `OUTPUT` unless error is recoverable.
4. Increment `sp.rev` by 1 and set `sp.fsm=next`.

## Constraints
- Deterministic transitions only.
- If `last.e.code` is unknown, treat as fatal.

## Failure modes
- `NO_LAST`: missing last output.
- Rollback: `rb=state`.

## Example I/O
Input
```json
{ "last": { "skill": "evidence-filter", "s": "ok", "e": null }, "st": { "sid": "A1", "rev": 9, "fsm": "SELECT_EVIDENCE" } }
```
Output
```json
{ "s": "ok", "d": { "next": "NLI_VERIFY", "sp": { "rev": 10, "fsm": "NLI_VERIFY" } }, "e": null, "rb": "none" }
```



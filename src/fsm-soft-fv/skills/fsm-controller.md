# FSM Controller Skill

## Purpose
This is the controller skill for the soft-FSM fact-verification agent.

## Main Flow
1. Parse and normalize claim.
2. Plan and execute retrieval.
3. Select high-signal evidence.
4. Score NLI stance.
5. Decide verdict.
6. Compose final output.

## Control Rules
1. Keep FSM transitions soft-constrained: retry/back allowed when signals are weak.
2. Keep reasoning stages LLM-led; avoid tool usage outside retrieval.
3. Prefer valid JSON over verbose text.
4. If uncertain at any reasoning stage, preserve uncertainty in labels (`neutral`, `insufficient`) instead of forcing certainty.

## Routing
Use `fsm-fact-verification.md` as the main policy and reference subskills in `skills/subskills/` for each state.

## Planner Output Contract
```json
{
  "a": "tool|advance|finish",
  "tool": "optional tool id",
  "args": {},
  "status": "ok|retry|back|error",
  "note": "short reason"
}
```

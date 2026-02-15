## Decide State

Goal:
- aggregate scores into verdict per claim

Do this with LLM reasoning in `write.verdicts`.
Prefer `insufficient` when evidence is weak or conflicting.

Exit condition:
- `verdicts` non-empty -> `OUTPUT`

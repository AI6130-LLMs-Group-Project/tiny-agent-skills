## NLI Verify State

Goal:
- decide support/refute/neutral per selected evidence-claim pair

Do this with LLM reasoning in `write.scores`.
Be conservative on weak or mismatched evidence.

Exit condition:
- `scores` non-empty -> `DECIDE`
- otherwise retry or go back to `RETRIEVAL`

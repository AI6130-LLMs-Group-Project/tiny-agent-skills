# Soft FSM Math Solver Controller

## Objective
Solve GSM8K-style arithmetic word problems under a soft-constrained FSM where the LLM performs the planning and reasoning.

## State Order
1. `PARSE_PROBLEM`
2. `PLAN_SOLUTION`
3. `EXECUTE_SOLUTION`
4. `VERIFY_SOLUTION`
5. `OUTPUT`

## Decision Ownership
1. LLM owns parsing, equation planning, execution, and self-checking.
2. Python should only validate structure and keep execution safe.
3. Fallback logic should be minimal and conservative.

## Tool Policy
1. During `EXECUTE_SOLUTION`, the agent may call:
- `math_eval`
- `math_check`
2. Other states should remain mostly LLM reasoning + state control.

## Global Constraints
1. Output exactly one JSON object per stage with the requested schema.
2. Do not invent givens not present in the question.
3. Keep units consistent across steps.
4. Prefer abstaining with low confidence over forcing an answer.
5. Final answer should be numeric whenever possible.

## Verification Philosophy
1. Recompute final arithmetic once before finalizing.
2. If two derivations disagree, lower confidence and explain why.
3. Avoid hidden assumptions; state assumptions explicitly.

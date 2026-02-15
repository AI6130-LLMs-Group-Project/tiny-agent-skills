## Parse Claim State

Goal:
- normalize the claim text
- split into atomic subclaims if needed
- produce retrieval plans

Do this with LLM reasoning in `write`:
- set `norm_claim`
- set `claims`
- set `plans`

Exit condition:
- non-empty `claims` and `plans`, then move to `RETRIEVAL`

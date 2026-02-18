# Subskill: Execute Math Solution

## Goal
Carry out the planned arithmetic and produce a numeric answer candidate.

## Output Contract
Return JSON:
```json
{
  "reasoning": "brief calculation narrative",
  "ans": "numeric answer or numeric string",
  "unit": "optional unit",
  "conf": "low|med|high"
}
```

## Constraints
1. Keep `reasoning` under 420 chars.
2. `ans` should be directly parseable as a number if possible.
3. If uncertain, lower confidence instead of guessing.

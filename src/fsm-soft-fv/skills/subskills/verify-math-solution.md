# Subskill: Verify Math Solution

## Goal
Check the proposed math answer against the question and plan.

## Output Contract
Return JSON:
```json
{
  "ok": true,
  "ans": "verified or revised numeric answer",
  "notes": "short verification note",
  "conf": "low|med|high"
}
```

## Constraints
1. Recompute the final arithmetic once.
2. If revised, set `ok` to false and provide corrected `ans`.
3. Keep `notes` under 220 chars.

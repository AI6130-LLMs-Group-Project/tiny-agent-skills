# Subskill: Math Output

## Goal
Format the final GSM8K answer for evaluation and trace printing.

## Output Contract
Return JSON:
```json
{
  "out": [
    {
      "id": "q1",
      "answer": "numeric answer",
      "conf": "low|med|high",
      "r": "short rationale"
    }
  ]
}
```

## Constraints
1. Exactly one output row for single-question GSM8K samples.
2. Keep rationale under 220 chars.
3. Keep answer machine-readable (prefer plain number).

# Subskill: Parse Math Problem

## Goal
Convert a GSM8K question into a structured representation for solving.

## Output Contract
Return JSON:
```json
{
  "nq": "normalized question text",
  "target": "what needs to be solved",
  "givens": ["short given fact 1", "short given fact 2"],
  "unit": "optional unit string"
}
```

## Constraints
1. Keep `nq` under 320 chars.
2. Do not add givens that are not implied by the question.
3. `target` should be one short sentence.

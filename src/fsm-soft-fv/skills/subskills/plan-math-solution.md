# Subskill: Plan Math Solution

## Goal
Produce a concise, verifiable solving plan from parsed problem info.

## Output Contract
Return JSON:
```json
{
  "plan": ["step 1", "step 2"],
  "checks": ["consistency check 1"]
}
```

## Constraints
1. Keep plan length between 2 and 6 steps.
2. Use operational language (add, subtract, multiply, divide, compare).
3. Include at least one arithmetic sanity check.

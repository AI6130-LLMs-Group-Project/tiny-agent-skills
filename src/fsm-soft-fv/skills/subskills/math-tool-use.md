# Subskill: Math Tool Use

## Goal
Decide whether to call a math utility tool or finish with a final numeric answer.

## Available Tools
1. `math_eval`: evaluate arithmetic expression safely.
2. `math_check`: compare two numeric values with tolerance.

## Output Contract
Return exactly one JSON object with one of two action modes:

Tool mode:
```json
{
  "a": "tool",
  "tool": "math_eval|math_check",
  "args": {}
}
```

Finish mode:
```json
{
  "a": "finish",
  "ans": 0,
  "reasoning": "short explanation",
  "conf": "low|med|high"
}
```

## Constraints
1. Use tool mode when arithmetic is non-trivial or needs checking.
2. Use finish mode only when answer is ready.
3. Keep reasoning compact and factual.

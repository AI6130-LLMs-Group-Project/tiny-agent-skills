# NLI Verification Subskill

## Goal
Classify each selected evidence item as support, refute, or neutral for its mapped claim.

## Input
```json
{
  "claims": [{"id":"s1","c":"..."}],
  "selected": [{"eid":"...","for":"s1","s":"..."}]
}
```

## Output Contract
```json
{
  "scores": [
    {"eid":"...","for":"s1","st":"support|refute|neutral","conf":"low|med|high"}
  ]
}
```

## Decision Rules
1. Support when core entity + predicate align, and key constraints (dates/numbers) are compatible.
2. Refute when explicit contradiction exists:
   - incompatible year/number for the same event/attribute
   - negation conflict on same predicate
   - opposite predicate relation (e.g., born/died, win/lose)
3. Neutral when overlap is weak, ambiguous, or incomplete.
4. Absence of evidence is not refutation.
5. Topic overlap alone is not support.
6. If entity matches but predicate missing, use `neutral`.

## Constraint Handling
1. If claim has a key year/number and evidence omits it, prefer `neutral`.
2. If claim and evidence give conflicting key year/number on same fact, prefer `refute`.
3. For copular claims (`X is Y`), require Y-type evidence, not just X mention.

## Confidence Rules
- `high`: explicit and direct claim-evidence match/contradiction.
- `med`: mostly clear but slightly incomplete.
- `low`: weak lexical overlap or uncertain interpretation.

## Anti-Bias Rules
1. Do not output `support` when there is only entity-level overlap.
2. Use `neutral` as default under uncertainty.
3. Prefer one strong `refute` over multiple weak `support` scores.

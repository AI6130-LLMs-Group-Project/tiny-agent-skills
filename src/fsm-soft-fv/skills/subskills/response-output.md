# Response Output Subskill

## Goal
Compose concise final decision objects from verdicts and selected citations.

## Input
```json
{
  "claims": [{"id":"s1","c":"..."}],
  "verdicts": [{"id":"s1","v":"...","conf":"..."}],
  "selected": [{"eid":"...","for":"s1"}]
}
```

## Output Contract
```json
{
  "out": [
    {"id":"s1","ver":"supported|refuted|mixed|insufficient","conf":"low|med|high","r":"...","cite":["eid"]}
  ]
}
```

## Writing Rules
1. Rationale must be short, factual, and claim-specific.
2. Do not hallucinate source names or unseen facts.
3. Include up to two evidence ids.
4. If verdict is `insufficient`, rationale must explicitly mention insufficiency.
5. Keep rationale <= 220 chars.
6. Mention contradiction explicitly for `refuted` when available.

## Rationale Templates
1. `supported`: "Evidence directly matches entity, predicate, and key constraints."
2. `refuted`: "Evidence contradicts the claim on a key constraint or predicate."
3. `mixed`: "Evidence contains both supporting and contradicting signals."
4. `insufficient`: "Available evidence is incomplete or non-specific for this claim."

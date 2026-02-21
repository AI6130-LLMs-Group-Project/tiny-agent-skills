# Evidence Selection Subskill

## Goal
Choose the most claim-resolving evidence snippets from retrieved candidates.

## Input
```json
{
  "claims": [{"id":"s1","c":"..."}],
  "evidence": [{"eid":"...","for":"s1","s":"...","cred":"low|med|high"}]
}
```

## Output Contract
```json
{
  "sel": [{"eid":"...","for":"s1"}]
}
```

## Progress Gate Mode (optional)
When asked for a quality gate instead of `sel`, return:
```json
{
  "status": "ok|back|retry",
  "conf": "low|med|high",
  "reason": "short reason"
}
```
Use `back` when current selected evidence is too weak/non-specific and retrieval should be expanded.
Use `retry` when selection can be improved from current evidence without new retrieval.
Use `ok` when selected evidence is good enough for NLI.
If selected evidence is very small or low confidence relative to available evidence, prefer `retry` or `back` over `ok`.

## Selection Rules
1. Select only from provided evidence ids.
2. Prefer snippets with direct entity + predicate overlap (not just topic overlap).
3. Prefer snippets containing key numbers/years if claim has them.
4. Prefer contradiction-bearing snippets when claim is likely false.
5. Select up to 5 items total.
6. Try to keep at least one candidate per subclaim.

## Ranking Rubric (LLM-internal)
1. Entity alignment score: 0-2
2. Predicate alignment score: 0-2
3. Constraint alignment (date/number/location): 0-2
4. Contradiction explicitness bonus: +0 to +2
5. Prefer highest total scores; break ties by higher credibility.

## Rejection Rules
- Do not select snippets that only mention entity but not predicate.
- Drop noisy snippets that are generic definitions with no claim relation.
- Drop near-duplicate snippets with the same factual content.

# Verdict Decision Subskill

## Goal
Aggregate per-evidence NLI scores into one verdict per subclaim.

## Input
```json
{
  "claims": [{"id":"s1","c":"..."}],
  "scores": [{"eid":"...","for":"s1","st":"...","conf":"..."}]
}
```

## Output Contract
```json
{
  "ver": [{"id":"s1","v":"supported|refuted|mixed|insufficient","conf":"low|med|high"}]
}
```

## Aggregation Policy
1. Contradiction has priority when refute evidence is strong and consistent.
2. Support requires clear dominance over refute.
3. Mixed evidence => `mixed`.
4. Sparse/weak evidence => `insufficient`.
5. Use confidence weighting: `high=3`, `med=2`, `low=1`.

## Suggested Rule-of-Thumb Thresholds
1. `refuted` if refute_score >= 3 and refute_score >= support_score + 1.
2. `supported` if support_score >= 3 and support_score >= refute_score + 1.
3. `mixed` if both support_score >= 2 and refute_score >= 2.
4. Otherwise `insufficient`.

## Confidence Policy
- `high`: strong dominance with high-confidence evidence.
- `med`: moderate dominance.
- `low`: mixed or weak signal.

## Conservative Policy
1. When close-call between `supported` and `insufficient`, choose `insufficient`.
2. When close-call between `refuted` and `insufficient`, choose `insufficient`.
3. Never emit `supported` or `refuted` without at least one non-low signal.

## Multi-claim Note
Decide each subclaim independently; do not merge before this stage.

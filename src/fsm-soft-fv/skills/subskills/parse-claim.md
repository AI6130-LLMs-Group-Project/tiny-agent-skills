# Parse Claim Subskill

## Goal
Convert raw user claim into verification-ready subclaims.

## Input
```json
{
  "claim": "string"
}
```

## Output Contract
```json
{
  "nc": "normalized claim string",
  "ct": "atomic|multi|question",
  "sd": true,
  "subs": [
    {"id": "s1", "c": "subclaim text"}
  ]
}
```

## Rules
1. Normalize punctuation/spacing and keep original factual meaning.
2. Split only when one sentence contains separable atomic facts.
3. If claim is atomic, return one subclaim `s1`.
4. Keep each subclaim <= 240 chars.
5. Preserve dates, numbers, and named entities exactly.
6. Do not add inferred facts that are not explicitly in the claim.
7. Keep negation words (`not`, `never`, `no`) intact.
8. Keep comparative/superlative meaning intact (`first`, `largest`, `only`).

## Split Checklist
1. Split on conjunctions when each side can be verified alone.
2. Keep one subclaim if conjunction is part of one atomic phrase.
3. Keep temporal qualifiers with the fact they modify.
4. Use deterministic ids: `s1`, `s2`, `s3`, ...

## Example
Input: `"Matteo Renzi was born and raised in Italy."`
Output: `subs=[{"id":"s1","c":"Matteo Renzi was born in Italy."},{"id":"s2","c":"Matteo Renzi was raised in Italy."}]`

# Retrieval Planning Subskill

## Goal
Produce short, high-precision search queries for each subclaim.

## Input
```json
{
  "claims": [{"id":"s1","c":"..."}]
}
```

## Output Contract
```json
{
  "plans": [
    {"id":"s1","q":["query 1","query 2"],"lim":4}
  ]
}
```

## Query Design Rules
1. Each query <= 8 tokens.
2. Prioritize: named entity + predicate + year/number.
3. Prefer 2-3 focused queries over many broad queries.
4. Avoid vague single-token queries.
5. If claim contains year/number, at least one query must include it.
6. Use disambiguating type terms when entity is ambiguous (film, person, city, album, etc).
7. Keep wording literal; avoid speculative paraphrases.

## Efficiency Rules
- Keep `lim` between 3 and 5.
- Avoid duplicate paraphrase queries.
- Prefer 2 queries per claim unless claim is complex.

## Query Bundle Pattern
1. Anchor query: `entity + key predicate`.
2. Constraint query: `entity + year/number/date`.
3. Optional disambiguation query: `entity + type`.

## Failure-Avoidance Rules
1. Do not emit empty query strings.
2. Do not emit the same query twice after normalization.
3. If entity missing, use the most specific noun phrase from claim.

## Example
For `"The World Trade Center was destroyed on September 11, 2001."`:
- `"World Trade Center destroyed 2001"`
- `"September 11 World Trade Center"`

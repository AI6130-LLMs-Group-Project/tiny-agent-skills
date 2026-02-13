# Claim Normalizer Skill

## Purpose
Normalize an input claim into a short, unambiguous statement and decide if decomposition is needed.

## When to use (FSM state)
- `PARSE_CLAIM`

## Inputs schema
```json
{
  "c": "string",        // raw claim text
  "ctx": "string|null", // optional user context
  "lang": "string",     // BCP-47 or short tag, e.g. "en"
  "st": { "sid": "string", "rev": "int", "fsm": "string" }
}
```

## Outputs schema
```json
{
  "s": "ok|error|retry",
  "d": {
    "nc": "string",              // normalized claim
    "ct": "atomic|multi|question",
    "sd": "bool",                // should decompose
    "sp": { "rev": "int", "fsm": "string" }
  },
  "e": { "code": "string", "msg": "string" } | null,
  "rb": "none|state"
}
```

## Allowed tools
- `tool.claim_normalize` (preferred deterministic path)

## Algorithm/logic steps
1. Trim whitespace, remove surrounding quotes, and collapse repeated spaces.
2. Rewrite as a single declarative sentence; keep proper nouns and numbers.
3. If multiple independent facts are joined by "and/or" or multiple clauses, set `ct=multi` and `sd=true`.
4. If the input is a question, convert to a declarative proposition and set `ct=question`.
5. Set `sp.fsm` to `PARSE_CLAIM` and increment `sp.rev` by 1.

## Constraints
- Output must be deterministic for identical inputs.
- `nc` must be <= 240 characters.
- Do not add new facts or qualifiers not present in input.
- If input is empty or non-linguistic, return `s=error`.

## Failure modes
- `EMPTY_CLAIM`: claim missing or length < 3.
- `NON_TEXT`: claim contains no letters or digits.
- Rollback: `rb=state` (no state change applied).

## Example I/O
Input
```json
{ "c": "Did NASA land on the Moon in 1969?", "ctx": null, "lang": "en", "st": { "sid": "A1", "rev": 3, "fsm": "PARSE_CLAIM" } }
```
Output
```json
{ "s": "ok", "d": { "nc": "NASA landed on the Moon in 1969.", "ct": "question", "sd": false, "sp": { "rev": 4, "fsm": "PARSE_CLAIM" } }, "e": null, "rb": "none" }
```



# Soft FSM Fact Verification Controller

## Objective
Run FEVER-style claim verification with a soft-constrained FSM where decision-heavy work stays inside the agent LLM.

## State Order
1. `PARSE_CLAIM`
2. `RETRIEVAL`
3. `SELECT_EVIDENCE`
4. `NLI_VERIFY`
5. `DECIDE`
6. `OUTPUT`

## Decision Ownership
1. LLM owns decomposition, relevance judgment, stance judgment, and verdict aggregation.
2. Tools are retrieval helpers, not final judges.
3. Python fallbacks should be safety nets only when LLM output is missing or invalid.

## Global Constraints
1. Output exactly one JSON object per stage and follow the stage schema.
2. Never fabricate evidence text, ids, or source metadata.
3. Treat weak topical overlap as `neutral` then `insufficient`, not `support`.
4. Use `refute` only on explicit contradiction, not mere absence of support.
5. Keep each claim/subclaim independent until final FEVER mapping.

## Verification Philosophy
1. Favor precision over aggressiveness.
2. A single strong contradiction is often enough for `refuted`.
3. `supported` needs direct entity + predicate + constraint alignment.
4. If evidence is partial or ambiguous, abstain (`insufficient`).

## Tool Policy
1. Retrieval-only tool scope:
- `search`
- `web_search`
- `page_fetch`
- `sentence_extract`
2. Non-retrieval stages should be LLM-only.

## Final Output Shape
```json
{
  "out": [
    {
      "id": "s1",
      "ver": "supported|refuted|mixed|insufficient",
      "conf": "low|med|high",
      "r": "short rationale",
      "cite": ["eid1", "eid2"]
    }
  ]
}
```

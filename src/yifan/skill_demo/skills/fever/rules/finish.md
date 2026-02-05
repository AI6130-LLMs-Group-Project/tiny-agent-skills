# Finish: Final Answer Determination

## When to Use
- Sufficient evidence gathered
- Dead end reached (no more productive actions)
- Step limit approaching (5-7 steps)

## Valid Answers
- **SUPPORTS**: Evidence confirms claim is true
- **REFUTES**: Evidence contradicts claim
- **NOT ENOUGH INFO**: Cannot verify from available information

## Decision Criteria

### SUPPORTS
- ✅ Core facts match observation
- ✅ Numbers/dates align (allow minor rounding)
- ✅ Logical equivalence (e.g., "first African American president" ≡ specific person)

### REFUTES
- ❌ Direct contradiction (different date, number, fact)
- ❌ Impossibility (claim says A, evidence proves not-A)
- ❌ Mutually exclusive statements

### NOT ENOUGH INFO
- ⚠️ Entity not found in Wikipedia
- ⚠️ Information exists but specific detail missing
- ⚠️ After 2 search attempts, still no relevant data
- ⚠️ Ambiguous phrasing with no clarifying info

## Output Format
```
Thought: [1 sentence summarizing evidence vs claim]
Action: finish[SUPPORTS/REFUTES/NOT ENOUGH INFO]
```

## Examples

### Example 1: SUPPORTS
Claim: "Python was created by Guido van Rossum."
Evidence: "Python was conceived by Guido van Rossum in the late 1980s."
```
Thought: Evidence confirms van Rossum created Python.
Action: finish[SUPPORTS]
```

### Example 2: REFUTES
Claim: "The Pacific Ocean is the smallest ocean."
Evidence: "The Pacific Ocean is the largest and deepest ocean..."
```
Thought: Evidence states Pacific is largest, contradicting "smallest."
Action: finish[REFUTES]
```

### Example 3: NOT ENOUGH INFO
Claim: "Jane Smith won the 2019 spelling bee."
Evidence: [After searching - Jane Smith page exists but no spelling bee mention]
```
Thought: No information found about Jane Smith and spelling bees.
Action: finish[NOT ENOUGH INFO]
```

### Example 4: Partial Match → SUPPORTS
Claim: "Mount Everest is approximately 29,000 feet tall."
Evidence: "Mount Everest stands at 29,032 feet (8,849 meters)."
```
Thought: 29,032 feet is approximately 29,000 feet - claim is supported.
Action: finish[SUPPORTS]
```

### Example 5: Related but Different → REFUTES
Claim: "Neil Armstrong walked on the Moon in 1970."
Evidence: "On July 20, 1969, Neil Armstrong became the first person to walk on the Moon."
```
Thought: Evidence shows 1969, not 1970 - claim is refuted.
Action: finish[REFUTES]
```

## Edge Cases

### Approximations
- "about", "approximately", "around" → Allow ±10% variance
- "over", "more than" → Must be strictly greater
- "nearly", "almost" → Allow ±5% variance

### Implicit Claims
- "the first X" → Verify chronological priority
- "only X" → Verify uniqueness (hard to support, often NEI)

### Temporal Issues
- Current facts may differ from knowledge cutoff
- Use "was" vs "is" to infer temporal claim

## Common Mistakes
- ❌ Overthinking: If evidence is clear, finish immediately
- ❌ Hedging: Choose definitive answer based on evidence
- ❌ Continuing: Don't search more after sufficient evidence
- ✅ Be decisive: 2-3 good pieces of evidence → finish
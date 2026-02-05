# After Lookup: Fact Extraction

## When to Use
- Previous action was lookup[string]
- Processing next sentence containing the string

## Observation Types

### Type A: Sentence Found
Next sentence in page containing the lookup string.

### Type B: String Not Found
"No match found" or similar error.

## Decision Process

```
Does sentence answer the claim?
├─ YES → Determine SUPPORTS/REFUTES
│   └─ finish[answer]
└─ NO → Can we lookup something else?
    ├─ YES (attempt < 2) → lookup[different keyword]
    └─ NO → finish[NOT ENOUGH INFO]
```

## Output Formats

### Case 1: Claim Verified
```
Thought: The sentence states [fact], which [matches/contradicts] the claim.
Action: finish[SUPPORTS/REFUTES]
```

### Case 2: Try Another Lookup
```
Thought: Sentence doesn't mention [key detail]. Will try a simpler part of the previous lookup string.
Action: lookup[sub-phrase from previous lookup]
```

### Case 3: No More Options
```
Thought: Insufficient information found to verify claim.
Action: finish[NOT ENOUGH INFO]
```

## Examples

### Example 1: Support Found
Claim: "The Great Wall of China is over 13,000 miles long."
Observation: "The total length of all sections is 13,171 miles."
```
Thought: 13,171 miles confirms "over 13,000 miles" is accurate.
Action: finish[SUPPORTS]
```

### Example 2: Refutation Found
Claim: "Shakespeare wrote 50 plays."
Observation: "Shakespeare wrote approximately 37 plays and 154 sonnets."
```
Thought: 37 plays contradicts the claim of 50 plays.
Action: finish[REFUTES]
```

### Example 3: Need Different Lookup
Claim: "The iPhone was released in 2008."
Observation: "The device revolutionized mobile phones."
```
Thought: This doesn't mention release year. Will lookup "2007" (likely year).
Action: lookup[released]
```

### Example 4: Dead End
Observation: "No match found"
```
Thought: Unable to find specific information after multiple attempts.
Action: finish[NOT ENOUGH INFO]
```

## Lookup Limits
- **Max 3 consecutive lookups**
- If those fail → finish[NOT ENOUGH INFO]
- Break down the previous lookup string into simpler parts (shorter sub-phrases)

## Keyword Selection Priority
1. Dates/numbers (1921, 13000, etc.)
2. Specific nouns (Nobel Prize, birthplace)
3. Verbs related to claim (won, born, invented)
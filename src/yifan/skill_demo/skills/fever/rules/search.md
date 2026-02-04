# After Search: Result Analysis

## When to Use
- Previous action was search[entity]
- Processing observation from Wikipedia

## Observation Types

### Type A: Entity Found (5 sentences returned)
Scan for claim-relevant facts in the sentences.

### Type B: Entity Not Found (Suggestions returned)
"Similar: [entity1, entity2, ...]"

## Decision Tree

```
Is answer directly in the 5 sentences?
├─ YES → finish[answer]
└─ NO → Is there a keyword to lookup?
    ├─ YES → lookup[keyword]
    └─ NO → Was entity found?
        ├─ YES → lookup[claim keyword]
        └─ NO → Try similar entity OR finish[NOT ENOUGH INFO]
```

## Output Formats

### Case 1: Answer Clear
```
Thought: The observation states [fact]. This [SUPPORTS/REFUTES] the claim.
Action: finish[SUPPORTS/REFUTES]
```

### Case 2: Need More Info
```
Thought: The page mentions [X] but not [Y]. Need to lookup [keyword].
Action: lookup[keyword]
```

### Case 3: Entity Not Found
```
Thought: Entity not found. Will try suggested alternative [entity].
Action: search[entity]
```

### Case 4: No Path Forward
```
Thought: No relevant information found after searching.
Action: finish[NOT ENOUGH INFO]
```

## Examples

### Example 1: Direct Answer
Observation: "Barack Obama (born August 4, 1961) is an American politician who served as the 44th president..."
Claim: "Barack Obama was the 44th president."
```
Thought: Observation confirms Obama was 44th president.
Action: finish[SUPPORTS]
```

### Example 2: Need Lookup
Observation: "World War II was a global war from 1939 to 1945..."
Claim: "World War II ended in 1946."
```
Thought: Observation says 1945, but need to confirm end date precisely.
Action: lookup[1945]
```

### Example 3: Entity Not Found
Observation: "Similar: [Mars, Mercury, Venus]"
Claim: "Marz is the fourth planet."
```
Thought: Typo likely - "Marz" not found. Will try Mars.
Action: search[Mars]
```

## Efficiency Rules
- If 2+ facts align → finish immediately
- If contradiction found → finish[REFUTES]
- Max 1 lookup attempt per search
- After 2 failed searches → finish[NOT ENOUGH INFO]
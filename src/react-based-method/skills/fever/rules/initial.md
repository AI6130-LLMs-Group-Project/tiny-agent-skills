# Initial Step: Entity Identification

## When to Use
- Step count: 0
- No previous actions

## Objective
Identify the PRIMARY entity to search for verification.

## Process
1. Parse the claim
2. Extract main subject (person, place, event, concept)
3. Formulate search query

## Selection Strategy
Priority order:
1. **Named entities** (people, organizations, locations)
2. **Specific events** (wars, discoveries, elections)
3. **Concepts** (if no named entities exist)

## Output Format
```
Thought: The claim is about [X]. I need to verify [specific aspect]. Will search for [entity].
Action: search[entity]
```

## Examples

### Example 1
Claim: "Marie Curie was born in Warsaw."
```
Thought: Need to verify Marie Curie's birthplace. Will search for her.
Action: search[Marie Curie]
```

### Example 2
Claim: "The Eiffel Tower was completed in 1889."
```
Thought: Need to verify Eiffel Tower completion date.
Action: search[Eiffel Tower]
```

### Example 3
Claim: "Photosynthesis produces oxygen."
```
Thought: Need to verify what photosynthesis produces.
Action: search[Photosynthesis]
```

## Common Mistakes to Avoid
- ❌ Searching for full claim text
- ❌ Searching for adjectives/modifiers
- ❌ Multiple thoughts before action
- ✅ Search ONE primary entity
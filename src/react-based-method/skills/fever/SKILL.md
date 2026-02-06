# ReAct Pattern for Fact Verification

## Overview
This skill enables fact verification through iterative reasoning and action. The model alternates between THOUGHT and ACTION steps to verify claims against Wikipedia knowledge.

## Core Pattern
```
Thought: [reasoning about what to do next]
Action: [one of: search[entity] | lookup[string] | finish[answer]]
Observation: [result from action]
```

## Workflow

1. **Read the claim** - Understand what needs verification
   - rules/initial.md` - Identify key entity to search
2. **Select appropriate subskill** based on current state:
   - `rules/search.md` - After search: analyze results and plan next action
   - `rules/lookup.md` - During lookup: extract relevant facts
   - `rules/finish.md` - When ready: determine final answer
3. **Execute action** - Perform exactly one action per turn
4. **Process observation** - Update understanding based on result
5. **Repeat** Repeat steps 2-4 until finish[answer] is called

## Action Constraints
- **search[entity]**: Returns first 5 sentences OR suggests similar entities
- **lookup[string]**: Returns next sentence containing the string
- **finish[answer]**: Must be SUPPORTS, REFUTES, or NOT ENOUGH INFO

## Key Principles
- One action per turn
- Keep thoughts concise (1-2 sentences)
- Focus on claim keywords

## Selection Logic
```
Current State → Subskill
─────────────────────────
No actions yet → initial.md (first step only)
After search[] → search.md
After lookup[] → lookup.md or finish.md
Ready to answer → finish.md
```

## Example Flow
```
Claim: "Albert Einstein won the Nobel Prize in Physics in 1921."

Subskill: initial
Thought: The claim is about Einstein. Need to verify Nobel Prize year. Will search for Albert Einstein.
Action: search[Albert Einstein]
Observation: [Returns bio mentioning Nobel Prize]

Subskill: search
Thought: Found Einstein page, need specific year info.
Action: lookup[Nobel Prize]
Observation: "He received the 1921 Nobel Prize in Physics..."

Subskill: lookup
Thought: Claim matches observation exactly.
Action: finish[SUPPORTS]
```


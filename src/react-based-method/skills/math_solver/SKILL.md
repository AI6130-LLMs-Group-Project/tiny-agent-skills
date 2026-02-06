# Plan-and-Solve Pattern for Math Problem Solving

## Overview
This skill enables systematic math problem solving through structured planning and execution. The model progresses through understanding, planning, calculating, and verification stages to solve word problems accurately.

## Core Pattern
```
Stage: [understand | plan | calculate | verify]
Thought: [reasoning about current stage]
Action: [one of: extract[variables] | plan[steps] | compute[expression] | answer[result]]
Observation: [result from action]
```

## Workflow

1. **Understand the problem** - Parse and extract information
   - `rules/understand.md` - Identify variables and numerals
2. **Devise a plan** - Create step-by-step solution strategy
   - `rules/plan.md` - Break down into calculable steps
3. **Execute calculations** - Perform each computation
   - `rules/calculate.md` - Calculate intermediate values
4. **Verify and answer** - Check work and present final answer
   - `rules/verify.md` - Validate result and format answer

## Action Constraints
- **extract[variables]**: Returns parsed variables with their numerical values
- **plan[steps]**: Returns numbered list of computational steps
- **compute[expression]**: Returns result of mathematical expression
- **answer[result]**: Returns final answer with units (if applicable)

## Key Principles
- One action per turn
- Keep thoughts concise but complete
- Track all intermediate values
- Pay attention to units and conversions
- Apply commonsense checks (reasonable magnitudes, physical constraints)

## Selection Logic
```
Current Stage → Subskill
─────────────────────────
Problem received → understand.md (first step only)
After extract[] → plan.md
After plan[] → calculate.md
During compute[] → calculate.md (continue)
All steps done → verify.md
```

## Example Flow
```
Problem: "A store sells apples for $2 each. If John buys 5 apples and pays with a $20 bill, how much change does he receive?"

Subskill: understand
Thought: The problem involves buying apples. I need to identify the price, quantity, and payment amount.
Action: extract[variables]
Observation:
- price_per_apple = $2
- quantity = 5
- payment = $20
- goal: find change received

Subskill: plan
Thought: To find the change, I need to calculate total cost first, then subtract from payment.
Action: plan[steps]
Observation:
1. Calculate total cost = price_per_apple × quantity
2. Calculate change = payment - total_cost

Subskill: calculate
Thought: First, I'll calculate the total cost of apples.
Action: compute[2 × 5 = 10]
Observation: total_cost = $10

Subskill: calculate
Thought: Now subtract from payment to find change.
Action: compute[20 - 10 = 10]
Observation: change = $10

Subskill: verify
Thought: John pays $20 for $10 worth of apples, so $10 change is correct. Sanity check: change < payment ✓
Action: answer[$10]
```

## Problem Types Supported
- Arithmetic word problems
- Rate/ratio problems
- Percentage calculations
- Multi-step reasoning
- Unit conversions
- Age/time problems
- Geometry (basic)
- Profit/loss calculations

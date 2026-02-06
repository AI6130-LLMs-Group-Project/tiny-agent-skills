# Plan: Devising the Solution Strategy

## When to Use
- Previous action was extract[variables]
- Variables and goal are identified
- Ready to create computation plan

## Objective
Create a complete, step-by-step plan that transforms known variables into the target answer.

## Planning Process
1. Identify the final goal (what we need to find)
2. Work backwards: what's needed to compute the goal?
3. Continue until all required values are known quantities
4. Reverse to get forward computation order
5. Number each step clearly

## Plan Structure
Each step should:
- Have exactly ONE computation
- Reference only known values or previously computed values
- State what intermediate variable it produces
- Include the formula or operation

## Output Format
```
Thought: To find [goal], I need [intermediate values]. Here's my plan.
Action: plan[steps]
```

Then list steps as:
```
Plan:
1. Calculate [intermediate_1] = [formula using known variables]
2. Calculate [intermediate_2] = [formula using known or step 1 result]
...
n. Calculate [goal] = [final formula]
```

## Examples

### Example 1: Two-Step Problem
Variables: price = $50, discount_rate = 20%
Goal: Find final_price
```
Thought: I need to calculate the discount amount first, then subtract from price.
Action: plan[steps]
```
Observation:
Plan:
1. Calculate discount_amount = price × discount_rate = 50 × 0.20
2. Calculate final_price = price - discount_amount

### Example 2: Rate × Time Problem
Variables: speed = 45 mph, time_part1 = 2 hours, time_part2 = 3 hours
Goal: Find total_distance
```
Thought: I need to calculate distance for each part, then add them together.
Action: plan[steps]
```
Observation:
Plan:
1. Calculate distance_1 = speed × time_part1 = 45 × 2
2. Calculate distance_2 = speed × time_part2 = 45 × 3
3. Calculate total_distance = distance_1 + distance_2

### Example 3: Percentage Problem
Variables: original = 80, new = 100
Goal: Find percent_increase
```
Thought: Percent increase requires finding the difference, then dividing by original.
Action: plan[steps]
```
Observation:
Plan:
1. Calculate difference = new - original = 100 - 80
2. Calculate percent_increase = (difference / original) × 100

### Example 4: Equation Solving
Variables: tom_age = 3x, son_age = x
Constraint: tom_age + 10 = 2(son_age + 10)
Goal: Find x (son's age), then tom_age
```
Thought: I need to set up and solve the equation, then calculate Tom's age.
Action: plan[steps]
```
Observation:
Plan:
1. Expand equation: 3x + 10 = 2(x + 10) = 2x + 20
2. Solve for x: 3x + 10 = 2x + 20 → 3x - 2x = 20 - 10 → x = 10
3. Calculate tom_age = 3x = 3 × 10

### Example 5: Multi-Part Problem
Variables: initial = $100, book_rate = 40%, lunch = $15
Goal: Find remaining_money
```
Thought: Need to calculate book spending from percentage, then subtract both expenses.
Action: plan[steps]
```
Observation:
Plan:
1. Calculate book_spending = initial × book_rate = 100 × 0.40
2. Calculate total_spent = book_spending + lunch
3. Calculate remaining_money = initial - total_spent

## Planning Best Practices
- Each step should be independently verifiable
- Avoid combining multiple operations in one step
- Keep track of units throughout
- Consider alternative approaches if one seems complex
- Check that plan covers the EXACT question asked

## Common Mistakes to Avoid
- Skipping steps (combine too many operations)
- Wrong operation order (percentage of wrong base)
- Missing unit conversions
- Computing something not asked for
- Circular dependencies between steps

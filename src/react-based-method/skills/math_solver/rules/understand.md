# Understand: Problem Parsing and Variable Extraction

## When to Use
- Step count: 0
- Problem just received
- No previous actions

## Objective
Parse the problem statement to extract all relevant variables, their numerical values, and identify what needs to be solved.

## Process
1. Read the problem carefully
2. Identify all quantities mentioned (numbers with context)
3. Assign meaningful variable names
4. Determine what the question asks for (the goal)
5. Note any implicit constraints or relationships

## Variable Extraction Strategy

### Explicit Variables
Look for:
- **Counts**: "5 apples", "3 workers", "12 hours"
- **Rates**: "$15 per hour", "60 miles per hour", "3 items per box"
- **Totals**: "total of $500", "altogether 25 students"
- **Percentages**: "20% discount", "15% tax"
- **Fractions**: "half the price", "one-third of the total"

### Implicit Variables
Identify:
- Starting values (often "initially", "at first", "originally")
- Final values (what we're solving for)
- Constraints (limits, conditions)
- Relationships between quantities

## Output Format
```
Thought: The problem is about [context]. I need to identify [what].
Action: extract[variables]
```

Then list variables as:
```
Variables:
- var_name_1 = value (unit)
- var_name_2 = value (unit)
- ...
Goal: Find [target variable]
Constraints: [any limits or conditions]
```

## Examples

### Example 1: Simple Purchase
Problem: "A shirt costs $25. Tax is 8%. What is the total cost?"
```
Thought: This is a tax calculation problem. I need to extract price and tax rate.
Action: extract[variables]
```
Observation:
- shirt_price = $25
- tax_rate = 8% = 0.08
- Goal: Find total_cost (price + tax)

### Example 2: Rate Problem
Problem: "A car travels at 60 mph. How far does it go in 2.5 hours?"
```
Thought: This is a distance = rate × time problem. I need speed and time.
Action: extract[variables]
```
Observation:
- speed = 60 mph
- time = 2.5 hours
- Goal: Find distance traveled
- Formula: distance = speed × time

### Example 3: Multi-Step Problem
Problem: "Maria has $100. She spends 40% on books and $15 on lunch. How much does she have left?"
```
Thought: This involves percentage spending and fixed spending from an initial amount.
Action: extract[variables]
```
Observation:
- initial_money = $100
- book_spending_rate = 40% = 0.40
- lunch_cost = $15
- Goal: Find remaining money
- Constraint: remaining >= 0

### Example 4: Age Problem
Problem: "Tom is 3 times as old as his son. In 10 years, Tom will be twice as old as his son. How old is Tom now?"
```
Thought: This is an age relationship problem with future constraints.
Action: extract[variables]
```
Observation:
- Let son_age = x (unknown, in years)
- tom_age = 3x (3 times son's age)
- Future: tom_age + 10 = 2(son_age + 10)
- Goal: Find tom_age (current)

## Common Mistakes to Avoid
- Missing hidden quantities ("each" implies per-unit rates)
- Confusing rates with totals
- Ignoring units (must track throughout)
- Missing the actual question being asked
- Not noting percentage base (percent OF what?)

## Commonsense Checks
- Do the numbers make sense in context?
- Are there physical constraints? (negative quantities, time limits)
- Is anything "per" something? (rates need careful handling)

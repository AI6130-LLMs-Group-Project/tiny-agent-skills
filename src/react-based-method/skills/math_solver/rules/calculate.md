# Calculate: Executing Computations Step by Step

## When to Use
- Previous action was plan[steps] or compute[expression]
- Have a plan to execute
- Working through computation steps

## Objective
Execute each planned computation accurately, tracking intermediate values.

## Calculation Process
1. Take the next step from the plan
2. Substitute known values into the expression
3. Compute the result carefully
4. Store the intermediate value
5. Repeat until all steps complete

## Output Format
```
Thought: Step N: Computing [variable_name] using [formula].
Action: compute[numerical_expression = result]
```

Observation format:
```
[variable_name] = [result] [unit if applicable]
```

## Arithmetic Rules

### Order of Operations (PEMDAS/BODMAS)
1. Parentheses/Brackets first
2. Exponents/Orders
3. Multiplication and Division (left to right)
4. Addition and Subtraction (left to right)

### Common Operations
- Addition: a + b
- Subtraction: a - b
- Multiplication: a × b or a * b
- Division: a ÷ b or a / b
- Percentage: x% of y = (x/100) × y
- Fraction: a/b of c = (a/b) × c

## Examples

### Example 1: Simple Multiplication
Plan step: Calculate total_cost = price × quantity = 25 × 4
```
Thought: Step 1: Computing total cost by multiplying price by quantity.
Action: compute[25 × 4 = 100]
```
Observation: total_cost = $100

### Example 2: Percentage Calculation
Plan step: Calculate discount = price × rate = 80 × 0.25
```
Thought: Step 1: Computing 25% discount on $80.
Action: compute[80 × 0.25 = 20]
```
Observation: discount = $20

### Example 3: Subtraction
Previous: discount = $20, price = $80
Plan step: Calculate final_price = price - discount
```
Thought: Step 2: Subtracting discount from original price.
Action: compute[80 - 20 = 60]
```
Observation: final_price = $60

### Example 4: Division
Plan step: Calculate speed = distance / time = 150 / 3
```
Thought: Step 1: Computing speed using distance ÷ time.
Action: compute[150 ÷ 3 = 50]
```
Observation: speed = 50 mph

### Example 5: Complex Expression
Plan step: Calculate area = 0.5 × base × height = 0.5 × 8 × 6
```
Thought: Step 1: Computing triangle area using formula.
Action: compute[0.5 × 8 × 6 = 24]
```
Observation: area = 24 square units

### Example 6: Multi-Step in Sequence
Variables: workers = 5, hours = 8, rate = $15/hour
Plan:
1. hours_total = workers × hours
2. total_pay = hours_total × rate

Step 1:
```
Thought: Step 1: Computing total work hours.
Action: compute[5 × 8 = 40]
```
Observation: hours_total = 40 hours

Step 2:
```
Thought: Step 2: Computing total pay from hours and rate.
Action: compute[40 × 15 = 600]
```
Observation: total_pay = $600

## Handling Decimals
- Keep at least 2 decimal places during intermediate steps
- Round only at the final answer (if required)
- For money: always use 2 decimal places

## Handling Fractions
- Convert to decimals OR keep as fractions
- Be consistent within a problem
- Common conversions:
  - 1/2 = 0.5
  - 1/3 ≈ 0.333
  - 1/4 = 0.25
  - 3/4 = 0.75

## Common Mistakes to Avoid
- Wrong order of operations
- Forgetting to carry the sign (negative numbers)
- Dividing in wrong order (a÷b ≠ b÷a)
- Decimal point errors
- Unit mismatches (hours vs minutes, dollars vs cents)

## Sanity Checks During Calculation
- Is the magnitude reasonable?
- Do the units work out correctly?
- Is the sign (positive/negative) correct?
- If doubling/halving, does result match expectation?

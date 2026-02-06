# Verify: Answer Validation and Final Response

## When to Use
- All planned computation steps completed
- Ready to present final answer
- Need to verify correctness before submitting

## Objective
Validate the computed answer through sanity checks and present the final result clearly.

## Verification Process
1. Check: Does the answer address the original question?
2. Check: Are the units correct?
3. Check: Is the magnitude reasonable?
4. Check: Does it satisfy any constraints?
5. Optional: Verify by alternative method or estimation
6. Format and present final answer

## Verification Checks

### Unit Check
- Final answer has appropriate units (dollars, miles, hours, etc.)
- Units are consistent with what was asked
- Compound units simplified correctly ($/hour, miles/gallon)

### Magnitude Check
- Is the number in a reasonable range for the context?
- Ages should be positive and typically 0-120
- Prices should be positive (usually)
- Percentages typically 0-100 (can exceed for growth)
- Physical quantities respect natural limits

### Constraint Check
- Does answer satisfy all stated conditions?
- Does it match any relationships in the problem?
- Plug answer back into original conditions if possible

### Estimation Check
- Does rough mental math agree?
- Is order of magnitude correct?
- Round numbers and verify ballpark

## Output Format
```
Thought: All steps complete. Verifying: [brief check summary]. Answer is reasonable/valid.
Action: answer[final_result with units]
```

## Examples

### Example 1: Simple Answer
Computed: change = $10
Original question: "How much change does John receive?"
```
Thought: John paid $20 for $10 of apples. $20 - $10 = $10. Positive, less than payment. Valid.
Action: answer[$10]
```

### Example 2: Percentage Answer
Computed: percent_increase = 25
Original question: "What is the percent increase?"
```
Thought: Increased from 80 to 100. (100-80)/80 = 20/80 = 0.25 = 25%. Reasonable increase.
Action: answer[25%]
```

### Example 3: Time Answer
Computed: total_time = 2.5 hours
Original question: "How long will the trip take?"
```
Thought: 150 miles at 60 mph = 2.5 hours. Estimation: ~3 hours for ~180 miles, so 2.5 is reasonable.
Action: answer[2.5 hours (or 2 hours 30 minutes)]
```

### Example 4: Age Problem
Computed: tom_age = 30
Original question: "How old is Tom now?"
Constraint: Tom is 3× son's age; in 10 years, Tom is 2× son's age
```
Thought: Tom = 30, Son = 10. Check: 30 = 3×10 ✓. In 10 years: 40 = 2×20 ✓. Both conditions satisfied.
Action: answer[Tom is 30 years old]
```

### Example 5: Money Remaining
Computed: remaining = $45
Original question: "How much money does Maria have left?"
Constraints: Started with $100, spent cannot exceed $100
```
Thought: $100 - $40 (books) - $15 (lunch) = $45. Total spent $55 < $100 ✓. Positive remainder ✓.
Action: answer[$45]
```

## Answer Formatting Guidelines

### Numbers
- Whole numbers: no decimals if exact (5, 100, 42)
- Decimals: round appropriately (2.5, 3.14, 0.25)
- Money: always 2 decimal places ($45.00 or $45)
- Large numbers: use commas (1,000,000)

### Units
- Always include units if applicable
- Use consistent notation (mph, km/h, $/hour)
- Convert to requested units if specified

### Alternatives
- Provide equivalent forms when helpful
- "2.5 hours (or 2 hours 30 minutes)"
- "25% (or 1/4)"
- "$3.50 (or 350 cents)"

## Common Mistakes to Avoid
- Answering a different question than asked
- Forgetting units
- Not checking constraints
- Over-precision (too many decimal places)
- Not simplifying when appropriate

## Edge Cases

### Negative Results
- Sometimes valid (debt, below sea level, temperature)
- Often signals an error (negative price, negative count)
- Verify against problem context

### Zero Results
- Can be valid (no change, break-even)
- Might indicate division error
- Confirm problem setup allows zero

### Very Large/Small Results
- Use scientific notation if needed
- Double-check for unit conversion errors
- Verify decimal point placement

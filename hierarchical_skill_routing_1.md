# Hierarchical Skill Routing System

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Enhanced Skill Definition Format](#enhanced-skill-definition-format)
  - [skill.yaml Structure](#skillyaml-structure)
- [Prompt Templates for Each Level](#prompt-templates-for-each-level)
  - [Level 0: Intent Router Prompt](#level-0-intent-router-prompt)
  - [Level 1: Skill Decomposer Prompt](#level-1-skill-decomposer-prompt)
  - [Level 2: Parameter Resolver Prompt](#level-2-parameter-resolver-prompt)
  - [Level 3: Executor](#level-3-executor)
  - [Level 4: Result Synthesizer Prompt](#level-4-result-synthesizer-prompt)
- [Implementation Strategy](#implementation-strategy)
  - [Core Router Class](#core-router-class)
  - [Pydantic Schemas](#pydantic-schemas)
- [Skill Registry Structure](#skill-registry-structure)
  - [Registry Format](#registry-format)
- [Usage Examples](#usage-examples)
  - [Example 1: Simple Composite Skill](#example-1-simple-composite-skill)
  - [Example 2: Nested Composite Skills](#example-2-nested-composite-skills)
  - [Example 3: Parallel Execution](#example-3-parallel-execution)
- [Directory Structure](#directory-structure)
- [Benefits of This Approach](#benefits-of-this-approach)
- [Advanced Features](#advanced-features)
  - [Conditional Execution](#conditional-execution)
  - [Dynamic Sub-Skill Selection](#dynamic-sub-skill-selection)
  - [Skill Caching](#skill-caching)
- [Next Steps](#next-steps)

## Architecture Overview

```
User Query
    ↓
┌─────────────────────────────────────────┐
│   Level 0: Intent Router                │
│   Determines which top-level skill(s)   │
│   are needed to fulfill the request     │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   Level 1: Skill Decomposer             │
│   If skill has sub-skills, breaks down  │
│   into atomic execution steps           │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   Level 2: Parameter Resolver           │
│   Determines parameters for each        │
│   sub-skill based on context            │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   Level 3: Executor                     │
│   Runs atomic skills, collects results  │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   Level 4: Result Synthesizer           │
│   Combines outputs from all sub-skills  │
└─────────────────────────────────────────┘
```

## Enhanced Skill Definition Format

### skill.yaml Structure

```yaml
# skills/email_workflow/skill.yaml
name: email_workflow
version: 1.0.0
type: composite  # or 'atomic'
description: Complete email management workflow

# Define the skill tree structure
sub_skills:
  - name: email_composer
    path: ./sub_skills/email_composer
    triggers: ["compose", "write", "draft"]
    
  - name: email_classifier
    path: ./sub_skills/email_classifier
    triggers: ["categorize", "classify", "organize"]
    
  - name: email_responder
    path: ./sub_skills/email_responder
    triggers: ["reply", "respond", "answer"]
    dependencies: ["email_classifier"]  # Must run after classifier

# Routing logic for this composite skill
routing:
  strategy: "parallel"  # or "sequential", "conditional"
  max_depth: 3  # Prevent infinite recursion
  
# Execution parameters
execution:
  allow_parallel: true
  timeout_per_skill: 30
  retry_on_failure: 2
```

## Prompt Templates for Each Level

### Level 0: Intent Router Prompt

**File: `prompts/intent_router.txt`**

```markdown
# Intent Router System Prompt

You are a skill routing agent. Given a user request, determine which skills are needed.

## Available Skills
{{skills_registry}}

## Task
Analyze the user request and output a structured plan:

```json
{
  "primary_skills": ["skill_name"],
  "execution_order": "parallel" | "sequential",
  "reasoning": "why these skills were selected",
  "estimated_complexity": 1-10
}
```

## Rules
- Choose the MINIMUM set of skills needed
- If multiple skills are needed, determine if they can run in parallel
- Complex requests may require composite skills with sub-skills
- Always explain your reasoning

## Examples

**Example 1: Single Skill**

User: "Compose an email to my team about the project update"

Output:
```json
{
  "primary_skills": ["email_composer"],
  "execution_order": "sequential",
  "reasoning": "Single task requiring only email composition",
  "estimated_complexity": 3
}
```

**Example 2: Multiple Skills**

User: "Organize my inbox and draft replies to urgent emails"

Output:
```json
{
  "primary_skills": ["email_classifier", "email_responder"],
  "execution_order": "sequential",
  "reasoning": "Must classify first to identify urgent emails, then respond",
  "estimated_complexity": 7
}
```

**Example 3: Parallel Execution**

User: "Summarize my meeting notes and check my calendar for tomorrow"

Output:
```json
{
  "primary_skills": ["note_summarizer", "calendar_checker"],
  "execution_order": "parallel",
  "reasoning": "Independent tasks that can be executed simultaneously",
  "estimated_complexity": 5
}
```
```

### Level 1: Skill Decomposer Prompt

**File: `prompts/skill_decomposer.txt`**

```markdown
# Skill Decomposer System Prompt

You decompose composite skills into executable sub-skill chains.

## Context
- Current skill: {{skill_name}}
- Available sub-skills: {{sub_skills}}
- User request: {{user_query}}
- Skill dependencies: {{dependencies}}

## Task
Create an execution plan with sub-skill calls:

```json
{
  "execution_plan": [
    {
      "step": 1,
      "sub_skill": "sub_skill_name",
      "trigger_reason": "why this sub-skill is needed",
      "depends_on": [],
      "parameters_needed": ["param1", "param2"]
    }
  ],
  "data_flow": {
    "step_1_output": "feeds into step_2.param_x"
  }
}
```

## Rules
- Respect dependency constraints defined in skill.yaml
- Minimize total steps while maintaining correctness
- Identify data flow between steps
- If a sub-skill is itself composite, note it for recursive decomposition
- Maximum depth: {{max_depth}}
- Mark steps that can run in parallel

## Example

**Skill:** email_workflow  
**Sub-skills:** [email_classifier, email_responder, email_sender]  
**Query:** "Reply to all urgent emails from yesterday"

Output:
```json
{
  "execution_plan": [
    {
      "step": 1,
      "sub_skill": "email_classifier",
      "trigger_reason": "Need to identify urgent emails from yesterday",
      "depends_on": [],
      "parameters_needed": ["time_filter", "priority_threshold"],
      "can_parallelize": false
    },
    {
      "step": 2,
      "sub_skill": "email_responder",
      "trigger_reason": "Generate replies for identified urgent emails",
      "depends_on": [1],
      "parameters_needed": ["email_list", "tone", "context"],
      "can_parallelize": false
    },
    {
      "step": 3,
      "sub_skill": "email_sender",
      "trigger_reason": "Send the drafted replies",
      "depends_on": [2],
      "parameters_needed": ["draft_emails", "send_immediately"],
      "can_parallelize": false
    }
  ],
  "data_flow": {
    "step_1_output": "urgent_emails → step_2.email_list",
    "step_2_output": "drafted_emails → step_3.draft_emails"
  }
}
```
```

### Level 2: Parameter Resolver Prompt

**File: `prompts/parameter_resolver.txt`**

```markdown
# Parameter Resolver System Prompt

You resolve parameters for skill execution based on context and previous results.

## Context
- Current step: {{step_number}}
- Sub-skill schema: {{skill_schema}}
- User query: {{user_query}}
- Previous results: {{previous_results}}
- Required parameters: {{required_params}}
- Optional parameters: {{optional_params}}

## Task
Generate parameter values following the skill schema:

```json
{
  "parameters": {
    "param1": "resolved_value",
    "param2": "resolved_value"
  },
  "resolution_method": {
    "param1": "from_user_query",
    "param2": "from_previous_step_1"
  },
  "confidence": 0.95,
  "missing_required": []
}
```

## Rules
- Extract values from user query when possible
- Use previous step results when referenced in data flow
- Apply sensible defaults for optional parameters
- Flag missing required parameters
- Validate against skill schema constraints
- If confidence < 0.7, request clarification

## Resolution Priority
1. Explicit values from user query
2. Values from previous step outputs (following data flow)
3. Context-based inference
4. Default values (for optional params only)
5. Flag as missing (for required params)

## Example

**Skill:** email_responder

**Schema:**
```json
{
  "required": ["email_list", "tone"],
  "optional": ["max_length", "include_greeting"]
}
```

**Context:**
- User query: "Reply professionally to urgent emails"
- Previous step output: {"urgent_emails": ["email1@ex.com", "email2@ex.com"], "count": 2}

**Output:**
```json
{
  "parameters": {
    "email_list": ["email1@ex.com", "email2@ex.com"],
    "tone": "professional",
    "max_length": 200,
    "include_greeting": true
  },
  "resolution_method": {
    "email_list": "from_previous_step_1.urgent_emails",
    "tone": "extracted_from_user_query",
    "max_length": "default_value",
    "include_greeting": "default_value"
  },
  "confidence": 0.92,
  "missing_required": []
}
```

**Example with Missing Parameters:**

**User query:** "Reply to emails"  
**Previous step output:** null

**Output:**
```json
{
  "parameters": {
    "tone": "neutral"
  },
  "resolution_method": {
    "tone": "default_value"
  },
  "confidence": 0.45,
  "missing_required": ["email_list"]
}
```
```

### Level 3: Executor

The executor is the runtime component that actually runs atomic skills. It uses the compiled skill prompts and schemas generated during the compilation phase.

**Execution Flow:**

```python
# Atomic skill execution
1. Load skill prompt from compiled bundle
2. Inject resolved parameters
3. Call LLM with structured output schema
4. Validate output against Pydantic schema
5. Return result or error
```

### Level 4: Result Synthesizer Prompt

**File: `prompts/result_synthesizer.txt`**

```markdown
# Result Synthesizer System Prompt

You combine results from multiple sub-skill executions into a coherent response.

## Context
- Original user query: {{user_query}}
- Execution plan: {{execution_plan}}
- Results: {{all_results}}
- Errors (if any): {{errors}}

## Task
Synthesize a final response:

```json
{
  "summary": "High-level summary of what was accomplished",
  "detailed_results": {
    "step_1": "outcome",
    "step_2": "outcome"
  },
  "user_message": "Natural language response to user",
  "next_actions": ["suggested follow-ups"],
  "success_rate": 0.85,
  "partial_failures": []
}
```

## Rules
- Present results in order of execution
- Highlight failures or partial successes clearly
- Suggest fixes for failed steps
- Format output naturally for the user
- Include relevant data from intermediate steps
- Calculate success rate based on completed vs failed steps
- Provide actionable next steps

## Example 1: Full Success

**Results:**
```json
{
  "step_1": {"classified": 5, "urgent": 2},
  "step_2": {"drafted_replies": 2, "failed": 0}
}
```

**Output:**
```json
{
  "summary": "Classified 5 emails and drafted 2 urgent replies",
  "detailed_results": {
    "classification": "Found 2 urgent emails out of 5 total",
    "response_generation": "Successfully drafted professional replies for both urgent emails"
  },
  "user_message": "I've reviewed your emails and drafted professional replies for the 2 urgent messages. Would you like to review them before sending?",
  "next_actions": ["Review drafted replies", "Send emails", "Archive remaining messages"],
  "success_rate": 1.0,
  "partial_failures": []
}
```

## Example 2: Partial Success

**Results:**
```json
{
  "step_1": {"classified": 5, "urgent": 2},
  "step_2": {"error": "API timeout", "drafted_replies": 0}
}
```

**Output:**
```json
{
  "summary": "Classified 5 emails, but failed to draft replies due to timeout",
  "detailed_results": {
    "classification": "Found 2 urgent emails out of 5 total",
    "response_generation": "Failed: API timeout after 30 seconds"
  },
  "user_message": "I successfully identified 2 urgent emails from your inbox, but encountered a timeout while trying to draft replies. Would you like me to retry the reply generation?",
  "next_actions": ["Retry email response generation", "Review urgent emails manually", "Adjust timeout settings"],
  "success_rate": 0.5,
  "partial_failures": ["step_2: API timeout"]
}
```
```

## Implementation Strategy

### Core Router Class

```python
# agent/routing/hierarchical_router.py

from typing import Dict, List, Any
import asyncio
from dataclasses import dataclass

@dataclass
class ExecutionContext:
    """Tracks execution state across skill hierarchy"""
    depth: int
    results: Dict[int, Any]
    user_query: str
    parent_skill: str = None

class HierarchicalSkillRouter:
    def __init__(self, skills_registry, llm_client, max_depth=3):
        self.skills = skills_registry
        self.llm = llm_client
        self.max_depth = max_depth
    
    async def execute(self, user_query: str, depth=0) -> Dict:
        """Main entry point for hierarchical skill execution"""
        
        if depth > self.max_depth:
            raise RecursionError(f"Max skill depth {self.max_depth} exceeded")
        
        # Level 0: Route to appropriate skill(s)
        intent = await self._route_intent(user_query)
        
        results = []
        
        # Execute each primary skill
        if intent["execution_order"] == "parallel":
            # Parallel execution
            tasks = [
                self._execute_skill(skill_name, user_query, depth)
                for skill_name in intent["primary_skills"]
            ]
            results = await asyncio.gather(*tasks)
        else:
            # Sequential execution
            for skill_name in intent["primary_skills"]:
                result = await self._execute_skill(skill_name, user_query, depth)
                results.append(result)
        
        # Level 4: Synthesize results
        final_output = await self._synthesize_results(
            user_query, intent, results
        )
        
        return final_output
    
    async def _execute_skill(self, skill_name: str, user_query: str, depth: int):
        """Execute a single skill (atomic or composite)"""
        skill = self.skills.get(skill_name)
        
        if skill.type == "atomic":
            # Direct execution for atomic skills
            return await self._execute_atomic(skill, user_query)
        
        elif skill.type == "composite":
            # Recursive decomposition for composite skills
            return await self._execute_composite(skill, user_query, depth + 1)
    
    async def _execute_composite(self, skill, user_query: str, depth: int):
        """Handle composite skills with sub-skills"""
        
        # Level 1: Decompose into sub-skill execution plan
        plan = await self._decompose_skill(skill, user_query)
        
        step_results = {}
        
        for step in plan["execution_plan"]:
            # Wait for dependencies to complete
            await self._wait_for_dependencies(step, step_results)
            
            # Level 2: Resolve parameters for this step
            params = await self._resolve_parameters(
                step, user_query, step_results, plan["data_flow"]
            )
            
            # Check if we have all required parameters
            if params.get("missing_required"):
                step_results[step["step"]] = {
                    "error": "missing_parameters",
                    "missing": params["missing_required"]
                }
                continue
            
            # Level 3: Execute (may recurse if sub-skill is composite)
            sub_skill_name = step["sub_skill"]
            
            # Create a modified query with resolved parameters
            param_context = self._create_param_context(
                user_query, params["parameters"]
            )
            
            result = await self._execute_skill(
                sub_skill_name, 
                param_context,
                depth
            )
            
            step_results[step["step"]] = result
        
        return step_results
    
    async def _execute_atomic(self, skill, user_query: str):
        """Execute an atomic skill using its compiled prompt"""
        
        # Load compiled prompt
        prompt = self._load_skill_prompt(skill)
        
        # Load schema for structured output
        schema = self._load_skill_schema(skill)
        
        # Call LLM with structured output
        result = await self.llm.generate(
            prompt=prompt,
            user_input=user_query,
            schema=schema
        )
        
        # Validate against Pydantic model
        validated = skill.validator.validate(result)
        
        return validated
    
    async def _route_intent(self, user_query: str) -> Dict:
        """Level 0: Determine which skills to use"""
        
        prompt = self._load_prompt("intent_router")
        skills_info = self._format_skills_registry()
        
        result = await self.llm.generate(
            prompt=prompt,
            context={
                "skills_registry": skills_info,
                "user_query": user_query
            },
            schema=IntentSchema
        )
        
        return result
    
    async def _decompose_skill(self, skill, user_query: str) -> Dict:
        """Level 1: Break composite skill into execution steps"""
        
        prompt = self._load_prompt("skill_decomposer")
        
        result = await self.llm.generate(
            prompt=prompt,
            context={
                "skill_name": skill.name,
                "sub_skills": skill.sub_skills,
                "user_query": user_query,
                "dependencies": skill.dependencies,
                "max_depth": self.max_depth
            },
            schema=DecompositionSchema
        )
        
        return result
    
    async def _resolve_parameters(
        self, 
        step: Dict, 
        user_query: str, 
        step_results: Dict,
        data_flow: Dict
    ) -> Dict:
        """Level 2: Resolve parameters for a sub-skill"""
        
        prompt = self._load_prompt("parameter_resolver")
        
        # Get previous results that this step depends on
        previous_results = {
            dep: step_results[dep] 
            for dep in step["depends_on"]
            if dep in step_results
        }
        
        # Get the schema for this sub-skill
        sub_skill = self.skills.get(step["sub_skill"])
        
        result = await self.llm.generate(
            prompt=prompt,
            context={
                "step_number": step["step"],
                "skill_schema": sub_skill.schema,
                "user_query": user_query,
                "previous_results": previous_results,
                "required_params": sub_skill.required_params,
                "optional_params": sub_skill.optional_params,
                "data_flow": data_flow
            },
            schema=ParameterSchema
        )
        
        return result
    
    async def _synthesize_results(
        self, 
        user_query: str, 
        intent: Dict, 
        results: List[Dict]
    ) -> Dict:
        """Level 4: Combine results into final response"""
        
        prompt = self._load_prompt("result_synthesizer")
        
        # Extract any errors
        errors = [r for r in results if "error" in r]
        
        result = await self.llm.generate(
            prompt=prompt,
            context={
                "user_query": user_query,
                "execution_plan": intent,
                "all_results": results,
                "errors": errors
            },
            schema=SynthesisSchema
        )
        
        return result
    
    async def _wait_for_dependencies(self, step: Dict, step_results: Dict):
        """Wait for dependent steps to complete"""
        for dep in step["depends_on"]:
            while dep not in step_results:
                await asyncio.sleep(0.1)
    
    def _create_param_context(self, user_query: str, parameters: Dict) -> str:
        """Create enriched query with resolved parameters"""
        param_str = "\n".join(f"{k}: {v}" for k, v in parameters.items())
        return f"{user_query}\n\nParameters:\n{param_str}"
    
    def _load_prompt(self, prompt_name: str) -> str:
        """Load a prompt template"""
        # Implementation details
        pass
    
    def _load_skill_prompt(self, skill) -> str:
        """Load compiled prompt for atomic skill"""
        # Implementation details
        pass
    
    def _load_skill_schema(self, skill):
        """Load Pydantic schema for atomic skill"""
        # Implementation details
        pass
    
    def _format_skills_registry(self) -> str:
        """Format skills for intent router"""
        # Implementation details
        pass
```

### Pydantic Schemas

```python
# agent/routing/schemas.py

from pydantic import BaseModel, Field
from typing import List, Dict, Literal, Optional

class IntentSchema(BaseModel):
    """Schema for intent router output"""
    primary_skills: List[str] = Field(description="Skills needed to fulfill request")
    execution_order: Literal["parallel", "sequential"] = Field(
        description="How to execute the skills"
    )
    reasoning: str = Field(description="Why these skills were selected")
    estimated_complexity: int = Field(ge=1, le=10, description="Complexity score")

class ExecutionStep(BaseModel):
    """Single step in execution plan"""
    step: int
    sub_skill: str
    trigger_reason: str
    depends_on: List[int] = Field(default_factory=list)
    parameters_needed: List[str]
    can_parallelize: bool = False

class DecompositionSchema(BaseModel):
    """Schema for skill decomposer output"""
    execution_plan: List[ExecutionStep]
    data_flow: Dict[str, str] = Field(
        description="How data flows between steps"
    )

class ParameterSchema(BaseModel):
    """Schema for parameter resolver output"""
    parameters: Dict[str, any]
    resolution_method: Dict[str, str]
    confidence: float = Field(ge=0.0, le=1.0)
    missing_required: List[str] = Field(default_factory=list)

class SynthesisSchema(BaseModel):
    """Schema for result synthesizer output"""
    summary: str
    detailed_results: Dict[str, str]
    user_message: str
    next_actions: List[str]
    success_rate: float = Field(ge=0.0, le=1.0)
    partial_failures: List[str] = Field(default_factory=list)
```

## Skill Registry Structure

### Registry Format

```python
# skills/registry.py

from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class SubSkill:
    name: str
    type: Literal["atomic", "composite"]
    path: str
    triggers: List[str]
    dependencies: List[str] = None
    sub_skills: Optional[Dict[str, 'SubSkill']] = None

@dataclass
class Skill:
    name: str
    version: str
    type: Literal["atomic", "composite"]
    description: str
    sub_skills: Optional[Dict[str, SubSkill]] = None
    routing: Optional[Dict] = None
    execution: Optional[Dict] = None

# Example registry
SKILL_REGISTRY = {
    "email_workflow": Skill(
        name="email_workflow",
        version="1.0.0",
        type="composite",
        description="Complete email management workflow",
        sub_skills={
            "email_classifier": SubSkill(
                name="email_classifier",
                type="atomic",
                path="skills/email_workflow/sub_skills/email_classifier",
                triggers=["categorize", "classify", "organize"]
            ),
            "email_responder": SubSkill(
                name="email_responder",
                type="composite",  # This can also have sub-skills!
                path="skills/email_workflow/sub_skills/email_responder",
                triggers=["reply", "respond", "answer"],
                dependencies=["email_classifier"],
                sub_skills={
                    "tone_analyzer": SubSkill(
                        name="tone_analyzer",
                        type="atomic",
                        path="skills/email_workflow/sub_skills/email_responder/tone_analyzer",
                        triggers=["analyze", "detect"]
                    ),
                    "draft_generator": SubSkill(
                        name="draft_generator",
                        type="atomic",
                        path="skills/email_workflow/sub_skills/email_responder/draft_generator",
                        triggers=["write", "compose"]
                    )
                }
            )
        },
        routing={
            "strategy": "sequential",
            "max_depth": 3
        },
        execution={
            "allow_parallel": False,
            "timeout_per_skill": 30,
            "retry_on_failure": 2
        }
    )
}
```

## Usage Examples

### Example 1: Simple Composite Skill

```python
# User query
user_query = "Organize my inbox and reply to urgent emails"

# Expected execution flow:
# 1. Intent Router identifies: ["email_workflow"]
# 2. Skill Decomposer breaks down into:
#    - Step 1: email_classifier
#    - Step 2: email_responder (depends on step 1)
# 3. Parameter Resolver:
#    - Step 1: {priority_threshold: "high"}
#    - Step 2: {email_list: <from step 1>, tone: "professional"}
# 4. Executor runs both steps sequentially
# 5. Result Synthesizer combines outputs

router = HierarchicalSkillRouter(SKILL_REGISTRY, llm_client)
result = await router.execute(user_query)
```

### Example 2: Nested Composite Skills

```python
# User query with nested skill execution
user_query = "Draft professional replies to urgent customer emails"

# Expected execution flow:
# 1. Intent Router: ["email_workflow"]
# 2. Decompose email_workflow:
#    - Step 1: email_classifier
#    - Step 2: email_responder (composite skill!)
# 3. Decompose email_responder (recursive):
#    - Step 2.1: tone_analyzer
#    - Step 2.2: draft_generator
# 4. Execute in order: classifier → tone_analyzer → draft_generator
# 5. Synthesize results from all 3 atomic executions

router = HierarchicalSkillRouter(SKILL_REGISTRY, llm_client, max_depth=3)
result = await router.execute(user_query)
```

### Example 3: Parallel Execution

```python
# User query requiring parallel skills
user_query = "Summarize my meeting notes and schedule follow-up meetings"

# Expected execution flow:
# 1. Intent Router: ["note_summarizer", "calendar_scheduler"]
#    execution_order: "parallel"
# 2. Both skills execute simultaneously
# 3. Results combined by synthesizer

router = HierarchicalSkillRouter(SKILL_REGISTRY, llm_client)
result = await router.execute(user_query)
```

## Directory Structure

```
skills/
├── registry.py
├── email_workflow/
│   ├── skill.yaml
│   ├── SKILL.md
│   ├── prompts/
│   │   ├── prompt_2b.txt
│   │   ├── prompt_3b.txt
│   │   └── prompt_7b.txt
│   ├── schemas/
│   │   └── tool_schema.py
│   └── sub_skills/
│       ├── email_classifier/
│       │   ├── skill.yaml
│       │   ├── SKILL.md
│       │   ├── prompts/
│       │   └── schemas/
│       └── email_responder/
│           ├── skill.yaml
│           ├── SKILL.md
│           ├── prompts/
│           ├── schemas/
│           └── sub_skills/
│               ├── tone_analyzer/
│               └── draft_generator/
│
agent/
├── routing/
│   ├── hierarchical_router.py
│   ├── schemas.py
│   └── prompts/
│       ├── intent_router.txt
│       ├── skill_decomposer.txt
│       ├── parameter_resolver.txt
│       └── result_synthesizer.txt
```

## Benefits of This Approach

1. **Modularity**: Skills can be composed from sub-skills like building blocks
2. **Reusability**: Sub-skills can be shared across multiple parent skills
3. **Scalability**: Tree structure handles complex workflows naturally
4. **Maintainability**: Each skill level has clear responsibilities
5. **Debuggability**: Execution trace shows exactly which sub-skills ran
6. **Flexibility**: Parallel and sequential execution strategies
7. **Context Awareness**: Data flows between dependent steps
8. **Error Resilience**: Partial failures don't crash entire workflow

## Advanced Features

### Conditional Execution

```yaml
# skill.yaml with conditional logic
routing:
  strategy: "conditional"
  conditions:
    - if: "step_1.output.urgent == true"
      then: ["email_responder"]
    - else: ["email_archiver"]
```

### Dynamic Sub-Skill Selection

```python
# Let the LLM decide which sub-skills to use
class DynamicRouter:
    async def select_sub_skills(self, user_query, available_sub_skills):
        """Use LLM to dynamically select relevant sub-skills"""
        prompt = """
        Given these available sub-skills: {sub_skills}
        And this user query: {query}
        
        Select the minimum set of sub-skills needed.
        """
        # LLM returns selected sub-skills dynamically
```

### Skill Caching

```python
# Cache results for repeated sub-skill calls
class CachedRouter(HierarchicalSkillRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
    
    async def _execute_atomic(self, skill, user_query):
        cache_key = f"{skill.name}:{hash(user_query)}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = await super()._execute_atomic(skill, user_query)
        self.cache[cache_key] = result
        return result
```

## Next Steps

1. **Implement Intent Router**: Start with the Level 0 routing logic
2. **Build Decomposer**: Create the skill breakdown system
3. **Add Parameter Resolution**: Implement context-aware parameter extraction
4. **Create Test Suite**: Test with nested composite skills
5. **Add Monitoring**: Track execution paths and performance
6. **Optimize Prompts**: Tune each level's prompt for your models

---

**Version:** 1.0.0  
**Last Updated:** January 29, 2026  
**Author:** Claude (Anthropic)

# Environment Setup

This project uses `uv` with Python 3.12.

```bash
uv sync
uv run python -m agent hello
```

## Install llama.cpp

```bash
mkdir -p runtime && cd runtime
git clone https://github.com/ggerganov/llama.cpp.git llama-cpp
cd llama-cpp
mkdir -p build && cd build
cmake .. -DLLAMA_BUILD_SERVER=ON
cmake --build . --target llama-server --config Release -j2
cd ../../..
```

### Windows (I made the process one-click)

Use the provided batch file to clone and build a static `llama-server.exe`:

```bat
script\setup_llama_cpp.bat
```

## Quickstart (Qwen3-VL server)

Install `llama.cpp` first, then download the model, then start the server:

```bash
# 1  create directories for models
mkdir -p runtime/models

# 2 download Qwen3-VL-2B model + mmproj
bash script/download_qwen3vl.sh

# 3 run the server
bash script/run_qwen3vl_server.sh
```

### Windows

```bat
REM 1 build llama.cpp (if not done yet)
script\setup_llama_cpp.bat

REM 2 download Qwen3-VL-2B model + mmproj
script\download_qwen3vl.bat

REM 3 run the server
script\run_qwen3vl_server.bat
```

# Tiny  Skills

## Project Proposal

**Version:** 2.0.1
**Date:** January 28, 2026  
**Author:** Yifan Xu
**Last Update:** January 29, 2026  
**Updated by:** Hanny Zhang

---

## Executive Summary

Tiny Agent Skills is an open-source framework that empowers users to create custom skills for small, locally-hosted language models (2B-7B parameters). The core innovation is a **user-friendly skill definition system** that automatically compiles human-readable skill documentation into optimized tool-calling schemas. Users simply write markdown documentation describing their domain expertise - the framework handles everything else: parsing patterns, compressing knowledge for small context windows, generating type-safe schemas, and validating model outputs.

This democratizes Claude's sophisticated skill system for the local AI community, enabling anyone to build domain-specific AI assistants without cloud dependencies.

---

## Problem Statement

### The Core Challenge

Claude's skills work because they contain rich, human-readable documentation that Claude can parse and convert into reliable actions. Small models (2B-7B) struggle with this due to:

1. **Limited context windows**: Cannot fit full skill documentation (16KB+)
2. **Weak reasoning**: Struggle to extract patterns from prose + code examples
3. **Poor function calling**: 2B-7B models have <60% accuracy on complex tool schemas
4. **No error recovery**: Cannot self-correct malformed tool calls

### The User Perspective Gap

Users want to teach small models domain-specific skills but face major barriers:

| What Users Want | Current Reality |
|----------------|-----------------|
| "Write a markdown file describing my skill" | Must manually create complex JSON schemas |
| "The model should understand my documentation" | Models ignore or misinterpret prose instructions |
| "It should just work with my 7B model" | Requires extensive prompt engineering for each model |
| "I want to share skills with my team" | No standardized format; everyone reinvents the wheel |

### What We're Building

A **skill authoring and compilation system** where users:
1. **Define** skills in natural markdown (no coding required for basic skills)
2. **Compile** automatically into model-optimized artifacts
3. **Share** skills with the community in standardized format
4. **Customize** with full control over validation and behavior

---

## Project Objectives

### Primary Goals

1. **User-Friendly Skill Definition**: Anyone can create skills by writing markdown documentation
2. **Automatic Optimization**: Framework compiles skills for different model tiers (2B/3B/7B)
3. **Reliable Execution**: Achieve 80%+ valid function calls from 7B models, 60%+ from 2B
4. **Community Extensibility**: Standardized format for sharing and customizing skills

### Success Metrics

**User Experience:**
- Non-programmers can create basic skills within 30 minutes
- Skills can be created, tested, and shared without writing any Python code
- Clear validation feedback when skills have errors
- Active community skill library with 20+ contributed skills

**Technical Performance:**
- Parse 100% of valid skill markdown successfully
- Generate correct Pydantic schemas from documentation
- 7B models: 80%+ syntactically correct tool calls
- 2B models: 60%+ syntactically correct tool calls
- Compilation time <10 seconds per skill

---

## Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                  USER: SKILL AUTHOR                      │
│           (Writes SKILL.md in plain markdown)            │
│  - Describes tools and capabilities in natural language  │
│  - Provides code examples showing correct patterns       │
│  - Lists critical constraints and warnings               │
│  - No Python/JSON coding required                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ One-click compile
                     ▼
┌─────────────────────────────────────────────────────────┐
│         SKILL COMPILATION PIPELINE (Automated)           │
│                                                          │
│  1. Markdown Parser                                      │
│     └─> Extract: tool descriptions, examples, rules     │
│                                                          │
│  2. Pattern Analyzer                                     │
│     └─> Infer: function signatures, types, constraints  │
│                                                          │
│  3. Tier Generator                                       │
│     └─> Create: optimized prompts for 2B/3B/7B models  │
│                                                          │
│  4. Schema Generator                                     │
│     └─> Output: Type-safe Pydantic models + validators  │
│                                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Generates artifacts
                     ▼
┌─────────────────────────────────────────────────────────┐
│          COMPILED SKILL BUNDLE (Shareable)               │
│  skills/                                                 │
│    my_skill/                                            │
│      ├─ SKILL.md              (original documentation)  │
│      ├─ skill.yaml            (metadata & config)       │
│      ├─ prompts/                                        │
│      │   ├─ prompt_a.txt                                │
│      │   ├─ prompt_b.txt                                │
│      │   └─ prompt_c.txt                                │
│      ├─ schemas/                                        │
│      │   └─ tool_schema.py    (Pydantic models)        │
│      └─ validators/                                     │
│          └─ validators.py     (auto-generated checks)   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Can be: shared, versioned, forked
                     ▼
┌─────────────────────────────────────────────────────────┐
│         USER TOOL CALLING RUNTIME                        │
│                                                          │
│  User Request → Intent Router → Skill Selector          │
│       │                                                  │                 │
│       ├─> Load  skill rounting prompt                    │
│       ├─> Inject schema for structured output           │
│       └─> Generate with user's local LLM                │
│                                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│    VALIDATION & FEEDBACK (Helps Users Improve Skills)   │
│  - Parse against generated Pydantic schema               │
│  - Check against extracted constraints                   │
│  - Provide clear error messages                          │
│  - Suggest fixes for common issues                       │
│  - Log patterns for skill improvement                    │
└──────────────────────────────────────────────────────────┘
```

### Core Innovation: User-Centric Skill Compilation

The heart of the system transforms user-written documentation into machine-executable schemas.

#### 1. Skill Definition Language

Users write skills in **natural markdown** with special conventions:

**Example: Custom Email Skill**

```markdown
# Email Management Skill

## Description
Helps users compose, categorize, and manage emails efficiently.

## Tools

### compose_email
Creates a well-structured email draft.

**Required:**
- `to`: email address
- `subject`: brief topic
- `body`: main message

**Optional:**
- `cc`: additional recipients
- `tone`: formal|casual|friendly

**Rules:**
- NEVER send emails automatically without user confirmation
- Always validate email format
- Keep subject lines under 60 characters

**Examples:**

✅ CORRECT:
```json
{
  "to": "colleague@company.com",
  "subject": "Q4 Report Review",
  "body": "Hi Sarah, I've reviewed the Q4 report...",
  "tone": "professional"
}
```

❌ WRONG:
```json
{
  "to": "invalid-email",  // Missing @ symbol
  "subject": "This is an extremely long subject line that goes on and on...",  // Too long
}
```

### categorize_email
Suggests appropriate folder/label for an email.

**Rules:**
- Output one of: [work, personal, urgent, newsletter, archive]
- Base decision on sender, subject, and urgency markers
```

#### 2. Automatic Schema Generation

Framework automatically generates type-safe schemas:

```python
# Auto-generated from markdown above
from pydantic import BaseModel, Field, validator
from typing import Literal

class ComposeEmail(BaseModel):
    """Creates a well-structured email draft."""
    
    to: str = Field(..., description="Email address")
    subject: str = Field(..., description="Brief topic")
    body: str = Field(..., description="Main message")
    cc: Optional[str] = Field(None, description="Additional recipients")
    tone: Optional[Literal["formal", "casual", "friendly"]] = None
    
    @validator('to')
    def validate_email(cls, v):
        """Always validate email format"""
        if '@' not in v:
            raise ValueError("Invalid email format")
        return v
    
    @validator('subject')
    def check_subject_length(cls, v):
        """Keep subject lines under 60 characters"""
        if len(v) > 60:
            raise ValueError("Subject too long (max 60 chars)")
        return v

class CategorizeEmail(BaseModel):
    """Suggests appropriate folder/label for an email."""
    
    category: Literal["work", "personal", "urgent", "newsletter", "archive"]
```


## User Workflow

### Creating a New Skill

```bash
# 1. Create skill directory
mkdir -p skills/my_skill

# 2. Write skill documentation
cat > skills/my_skill/SKILL.md << 'EOF'
# My Custom Skill
[User writes natural markdown documentation]
EOF

# 3. Compile skill (one command)
tiny-claude compile skills/my_skill

# Output:
# ✓ Parsed documentation
# ✓ Generated 3 tier prompts (2B: 847 tokens, 3B: 1.5K tokens, 7B: 2.8K tokens)
# ✓ Created Pydantic schemas (2 tools detected)
# ✓ Added validation rules (5 constraints)
# ✓ Skill ready: skills/my_skill/

# 4. Test with your model
tiny-claude test skills/my_skill --model qwen-7b --query "Compose email to team"

```

---

## Implementation Plan

### Phase 1: Core Skill Compiler

**Goal:** Users can define and compile basic skills

**Deliverables:**
- Markdown parser: Extract tools, rules, examples
- Schema generator: Pydantic models from documentation
- CLI tool: `tiny-claude compile [skill_path]`

**Success Criteria:**
- Compile 5 example skills (email, calendar, note-taking, search, summary)
- Generate valid schemas for all tools
- Create tier-appropriate prompts

### Phase 2: Validation & Testing Framework

**Goal:** Users get clear feedback on skill quality

**Deliverables:**
- Skill validator: Check completeness, suggest improvements
- Test harness: Run skills against local models
- Metrics dashboard: Track success rates per tool/tier
- Error analyzer: Common failure patterns

### Phase 3: Community Infrastructure

**Goal:** Users can share and discover skills

**Deliverables:**
- Skill registry: Searchable community catalog
- Version management: Git-based skill evolution
- Dependency system: Skills can build on other skills
- Documentation site: Tutorials, best practices, examples


### Phase 4: Advanced Features (Weeks 13-16)

**Goal:** Power users can customize deeply

**Deliverables:**
- Custom validators: User-written validation logic
- Multi-skill workflows: Chain skills together
- Skill analytics: Usage patterns, optimization suggestions
- Integration helpers: Easy deployment in apps

---

## Technology Stack

### User-Facing Tools
- **CLI**: Typer (Python) - intuitive commands
- **Configuration**: YAML - human-readable skill metadata
- **Documentation**: Markdown - universal, accessible format

### Core Framework
- **Parser**: Python AST + regex for code extraction
- **Schema Generation**: Pydantic V2 - type-safe, validated models
- **Validation**: Custom rule engine built on Pydantic
- **Testing**: Pytest + hypothesis for property testing

### Model Integration
- **Inference**: llama.cpp + Instructor for structured outputs
- **Supported Models**: Any GGUF model with function calling
- **Optimization**: Per-tier prompt templates

### Community Platform
- **Registry**: GitHub repos + JSON catalog
- **Versioning**: Git + semantic versioning
- **Discovery**: Search API + web interface

---

## Differentiation from Existing Tools

| Feature | Tiny Agent Skills | LangChain Tools | Semantic Kernel | OpenAI Functions |
|---------|-------------------|-----------------|-----------------|------------------|
| **Markdown-based authoring** | ✅ Yes | ❌ Code only | ❌ Code only | ❌ JSON only |
| **Automatic schema generation** | ✅ Yes | ❌ Manual | ❌ Manual | ❌ Manual |
| **Multi-tier optimization** | ✅ 2B/3B/7B | ❌ One size | ❌ One size | ❌ Cloud only |
| **Validation layer** | ✅ Built-in | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic |
| **Community sharing** | ✅ Registry | ⚠️ Scattered | ⚠️ Limited | ❌ No |
| **Non-programmer friendly** | ✅ Yes | ❌ Requires coding | ❌ Requires coding | ❌ Requires coding |
| **Local model support** | ✅ Primary focus | ⚠️ Secondary | ⚠️ Secondary | ❌ Cloud only |

**Key Advantage:** We're the only framework designed for **non-programmers to author skills** that work reliably with **small local models**.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Users write invalid markdown** | Validator catches errors with helpful messages |
| **Models ignore skill instructions** | Multiple tiers + extensive testing ensure reliability |
| **Skills don't generalize** | Community feedback loop + analytics identify issues |
| **Adoption is slow** | Focus on 5 killer skills first, then expand |
| **Schema generation fails** | Fallback to manual schema editing |

---


## Why This Matters

This project democratizes sophisticated AI capabilities by enabling:

1. **Domain Experts**: Encode specialized knowledge without coding
2. **Privacy**: Keep sensitive data local, no cloud dependencies
3. **Customization**: Tailor AI behavior to specific needs
4. **Community**: Share and build on each other's skills
5. **Accessibility**: Run powerful AI on consumer hardware

Most importantly, it proves that **small local models can be as capable as cloud giants** when given the right structure and guidance.

---

## Call to Action

**For Contributors:**
- Help build the skill compiler and validation framework
- Create example skills in your domain of expertise
- Test with different local models and report findings

**For Early Adopters:**
- Define a skill for your use case
- Provide feedback on authoring experience
- Share your skill with the community

**For the Ecosystem:**
- This creates a standard for local AI skill definition
- Opens up research opportunities in efficient tool use
- Builds infrastructure for the post-API AI era

---

## Appendices

### Appendix A: Skill Definition Template

```markdown
# [Skill Name]

## Description
[1-2 sentence overview of what this skill does]

## Tools

### [tool_name]
[Brief description of tool purpose]

**Required:**
- `param1`: description
- `param2`: description

**Optional:**
- `param3`: description

**Rules:**
- CRITICAL constraint 1
- CRITICAL constraint 2

**Examples:**

✅ CORRECT:
```json
{
  "param1": "value",
  "param2": "value"
}
```

❌ WRONG:
```json
{
  "param1": "bad_value"  // Why this is wrong
}
```

[Repeat for each tool]
```

### Appendix B: Compilation Pipeline Details

```
SKILL.md
  ↓
[Parse Markdown]
  ├─> Extract tools (names, descriptions)
  ├─> Extract parameters (types, requirements)
  ├─> Extract rules (constraints, warnings)
  ├─> Extract examples (correct + incorrect)
  ↓
[Analyze Patterns]
  ├─> Infer types from examples
  ├─> Detect validation rules from constraints
  ├─> Score complexity for tier assignment
  ↓
[Generate Artifacts]
  ├─> Pydantic schemas (tool_schema.py)
  ├─> Validators (validators.py)
  ├─> Tier 1 prompt (ultra-compressed, 2B)
  ├─> Tier 2 prompt (compressed, 3B)
  ├─> Tier 3 prompt (full capability, 7B)
  ├─> Skill metadata (skill.yaml)
  ↓
[Package]
  └─> Complete skill bundle ready for:
      - Local testing
      - Community sharing
      - Version control
```


**End of Proposal**

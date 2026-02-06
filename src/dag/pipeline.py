"""
DAG pipeline orchestration: step order is defined by the graph; no LLM chooses "which skill next".

- Context: shared dict (evidence pool); each skill reads/writes it.
- Step: binds a skill_id; optional goto_if for conditional jump (e.g. back to retrieve when evidence is insufficient).
- Runner: executes steps in order; no LLM in the loop for routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

# -----------------------------------------------------------------------------
# Skill protocol: input context -> output updates (merged into context)
# -----------------------------------------------------------------------------


class Skill(Protocol):
    """
    Single skill: one step in the DAG.

    Input:  context (dict) — shared state from previous steps.
    Output: dict — updates to merge into context (e.g. {"queries": [...], "last_step": "query_gen"}).
    """

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run one step. Returns key-value updates to merge into context."""
        ...


SkillCallable = Callable[[dict[str, Any]], dict[str, Any]]


def as_skill(fn: SkillCallable) -> Skill:
    """Wrap a (context) -> updates callable as a Skill."""
    class Wrapper:
        def run(self, context: dict[str, Any]) -> dict[str, Any]:
            return fn(context)
    return Wrapper()


# -----------------------------------------------------------------------------
# Pipeline definition
# -----------------------------------------------------------------------------


@dataclass
class StepDef:
    """
    One node in the DAG.

    Input (from config):
      skill_id: which skill to run (must exist in registry).
      goto_if: optional (condition_str, step_index) — if condition holds after this step, jump to step_index (e.g. back to retrieve).
    """

    skill_id: str
    goto_if: None | tuple[str, int] = None  # e.g. ("evidence_count < 2", 1) -> jump to step 1 when condition is true


@dataclass
class PipelineConfig:
    """
    DAG definition: ordered steps and max step count (to avoid infinite loops).

    Input:  steps (list of StepDef), max_steps (int).
    Output: config.dag_str yields a string like "query_gen → retrieve → evidence_extract → verify → output".
    """

    steps: list[StepDef]
    max_steps: int = 100

    @property
    def dag_str(self) -> str:
        """Human-readable step order for logging."""
        return " → ".join(s.skill_id for s in self.steps)


# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------


@dataclass
class StepResult:
    """Result of a single step (for optional logging)."""
    step_index: int
    skill_id: str
    updates: dict[str, Any]
    goto: None | int = None


class PipelineRunner:
    """
    Executes the DAG: for each step, look up the skill, run it, merge updates into context; support goto_if for loops.

    Input:  config (PipelineConfig), registry (dict[str, Skill]).
    Output: run(initial_context) -> final context (dict) after all steps.
    """

    def __init__(self, config: PipelineConfig, registry: dict[str, Skill]):
        self.config = config
        self.registry = registry

    def run(self, initial_context: dict[str, Any]) -> dict[str, Any]:
        """
        Run the pipeline.

        Input:  initial_context — e.g. {"claim": "Newton was born in 1643."}.
        Output: final context — e.g. {"claim": ..., "queries": [...], "evidence": [...], "label": "Support", "output": "..."}.
        """
        ctx = dict(initial_context)
        step_index = 0
        total_steps = 0

        while step_index < len(self.config.steps) and total_steps < self.config.max_steps:
            step = self.config.steps[step_index]
            skill = self.registry.get(step.skill_id)
            if skill is None:
                raise ValueError(f"Unknown skill_id: {step.skill_id}")
            updates = skill.run(ctx)
            ctx |= updates
            total_steps += 1

            next_index = self._eval_goto(step, ctx)
            if next_index is not None:
                step_index = next_index
            else:
                step_index += 1

        return ctx

    def _eval_goto(self, step: StepDef, context: dict[str, Any]) -> None | int:
        """
        Input:  step (with optional goto_if), context.
        Output: target step_index if condition holds, else None.
        """
        if step.goto_if is None:
            return None
        condition, target_index = step.goto_if
        if self._eval_condition(condition, context):
            return target_index
        return None

    def _eval_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """
        Simple condition: "key < N", "key >= N", "key <= N", "key > N", "key == N", "key != N".
        If key's value is a list, its length is used.
        """
        for op in ("<", ">=", "<=", ">", "==", "!="):
            if op in condition:
                key_part, val_part = condition.split(op, 1)
                key = key_part.strip()
                try:
                    val = int(val_part.strip())
                except ValueError:
                    return False
                actual = context.get(key)
                if actual is None:
                    return False
                if isinstance(actual, list):
                    actual = len(actual)
                if not isinstance(actual, (int, float)):
                    return False
                if op == "<":
                    return actual < val
                if op == ">=":
                    return actual >= val
                if op == "<=":
                    return actual <= val
                if op == ">":
                    return actual > val
                if op == "==":
                    return actual == val
                if op == "!=":
                    return actual != val
        return False


# -----------------------------------------------------------------------------
# Load PipelineConfig from YAML
# -----------------------------------------------------------------------------


def load_pipeline_config_from_yaml(data: dict[str, Any]) -> PipelineConfig:
    """
    Build PipelineConfig from a parsed YAML dict.

    Input:  data — e.g. {"steps": [{"skill": "query_gen"}, ...], "max_steps": 100}.
    Output: PipelineConfig with StepDef list and optional goto_if from "goto_if: {condition: ..., step: N}".
    """
    steps_raw = data.get("steps", [])
    steps: list[StepDef] = []
    for s in steps_raw:
        if isinstance(s, str):
            steps.append(StepDef(skill_id=s))
        else:
            skill_id = s.get("skill") or s.get("skill_id")
            goto = s.get("goto_if")
            goto_if = None
            if goto is not None:
                if isinstance(goto, dict):
                    cond = goto.get("condition", "")
                    step = int(goto.get("step", 0))
                    goto_if = (cond, step)
                elif isinstance(goto, list) and len(goto) == 2:
                    goto_if = (str(goto[0]), int(goto[1]))
            steps.append(StepDef(skill_id=skill_id, goto_if=goto_if))
    max_steps = int(data.get("max_steps", 100))
    return PipelineConfig(steps=steps, max_steps=max_steps)

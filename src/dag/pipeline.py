"""
Pipeline / DAG 编排：由图结构决定执行顺序，小模型只在各节点内执行单一 skill。

- Context：共享的 evidence pool（dict），各 skill 读/写。
- Step：绑定一个 skill_id，可选 loop 条件（如证据不足则回到某步）。
- Runner：按序执行 step，无 LLM 做「选哪个 skill」的决策。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

# -----------------------------------------------------------------------------
# Skill 协议：接收当前 context，返回要合并进 context 的更新（或完整新 context）
# -----------------------------------------------------------------------------


class Skill(Protocol):
    """单个 skill：接收共享 context，返回本步产出（会合并进 context）。"""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """执行一步，返回要合并进 context 的字段。"""
        ...


# 也可用可调用对象代替
SkillCallable = Callable[[dict[str, Any]], dict[str, Any]]


def as_skill(fn: SkillCallable) -> Skill:
    """把 (context) -> updates 包装成 Skill。"""
    class Wrapper:
        def run(self, context: dict[str, Any]) -> dict[str, Any]:
            return fn(context)
    return Wrapper()


# -----------------------------------------------------------------------------
# Pipeline 定义
# -----------------------------------------------------------------------------


@dataclass
class StepDef:
    """管道中的一步：执行哪个 skill，以及可选的「之后跳转」规则。"""
    skill_id: str
    # 可选：执行完本步后，若 condition 满足则跳转到 step_index（用于「证据不足→回到检索」）
    goto_if: None | tuple[str, int] = None  # ("evidence_count < 2", 1) -> 若满足则跳到 step 1


@dataclass
class PipelineConfig:
    """管道配置：步骤列表 + 可选最大步数（防死循环）。"""
    steps: list[StepDef]
    max_steps: int = 100

    @property
    def dag_str(self) -> str:
        """DAG 的步骤顺序，用于打印/日志。"""
        return " → ".join(s.skill_id for s in self.steps)


# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------


@dataclass
class StepResult:
    """单步执行结果。"""
    step_index: int
    skill_id: str
    updates: dict[str, Any]
    goto: None | int = None  # 若不为 None，Runner 会跳转到该 step_index


class PipelineRunner:
    """按配置顺序执行 step，每步调用对应 skill，合并结果到 context；支持 goto 实现循环。"""

    def __init__(
        self,
        config: PipelineConfig,
        registry: dict[str, Skill],
    ):
        self.config = config
        self.registry = registry

    def run(self, initial_context: dict[str, Any]) -> dict[str, Any]:
        """执行管道，返回最终 context。"""
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

            # 检查是否要跳转（如「证据不足 → 回到检索」）
            next_index = self._eval_goto(step, ctx)
            if next_index is not None:
                step_index = next_index
            else:
                step_index += 1

        return ctx

    def _eval_goto(self, step: StepDef, context: dict[str, Any]) -> None | int:
        """若配置了 goto_if 且条件满足，返回目标 step_index，否则返回 None。"""
        if step.goto_if is None:
            return None
        condition, target_index = step.goto_if
        # 粗略实现：用简单规则，例如 "evidence_count < 2" 从 context 取 evidence_count 比较
        if self._eval_condition(condition, context):
            return target_index
        return None

    def _eval_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """简单条件求值：仅支持 'key < N' / 'key >= N' / 'key <= N'。"""
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
# 从 YAML 加载 PipelineConfig（可选）
# -----------------------------------------------------------------------------


def load_pipeline_config_from_yaml(data: dict[str, Any]) -> PipelineConfig:
    """从已解析的 YAML dict 构建 PipelineConfig。"""
    steps_raw = data.get("steps", [])
    steps: list[StepDef] = []
    for s in steps_raw:
        if isinstance(s, str):
            steps.append(StepDef(skill_id=s))
        else:
            skill_id = s.get("skill") or s.get("skill_id")
            goto = s.get("goto_if")  # 期望 "evidence_count < 2" -> 1 或 {"condition": "...", "step": 1}
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

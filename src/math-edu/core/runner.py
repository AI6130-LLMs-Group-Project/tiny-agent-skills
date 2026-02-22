import os
from typing import Optional

from run_skill import run_skill
from .models import MathEduConfig, SKILL_STOP_SUBSKILL


class MathEduRunner:
    def __init__(self, project_root: str, config: Optional[MathEduConfig] = None):
        self.project_root = os.path.abspath(project_root)
        self.config = config or MathEduConfig()

    def skill_dir(self, skill_name: str) -> str:
        # 修复：不要重复拼接 tiny_agent_skills_v2
        return os.path.join(self.project_root, "skills", skill_name)

    def run(self, task: str, skill_name: str, tools_registry=None) -> dict:
        if skill_name not in SKILL_STOP_SUBSKILL:
            raise ValueError(f"Unknown skill: {skill_name}")
        if not isinstance(task, str) or not task.strip():
            raise ValueError("Task is empty")

        sdir = self.skill_dir(skill_name)
        if not os.path.isdir(sdir):
            raise FileNotFoundError(f"Skill directory not found: {sdir}")
        if not os.path.isfile(os.path.join(sdir, "SKILL.md")):
            raise FileNotFoundError(f"SKILL.md not found: {sdir}")

        result = run_skill(
            task=task.strip(),
            skill_dir=sdir,
            base_url=self.config.base_url,
            model=self.config.model,
            tools_registry=tools_registry,
            max_steps=self.config.max_steps,
            stop_subskill=SKILL_STOP_SUBSKILL[skill_name],
            stop_on_answer=self.config.stop_on_answer,
        )

        if not isinstance(result, dict):
            raise TypeError("run_skill must return a dict")

        result.setdefault("steps", [])
        result.setdefault("final_answer", None)
        result.setdefault("diagnosis", None)
        return result

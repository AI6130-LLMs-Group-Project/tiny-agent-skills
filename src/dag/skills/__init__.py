"""事实核查 pipeline 的 skills，接本地 LLM 接口。"""

from .llm_skills import fact_check_skill_registry

__all__ = ["fact_check_skill_registry"]

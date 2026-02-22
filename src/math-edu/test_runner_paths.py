import os
from core.runner import MathEduRunner
from core.models import MathEduConfig


def test_skill_dir_no_duplicate_project_name():
    root = r"e:\NTU\LLM\tiny_agent_skills_v2"
    r = MathEduRunner(project_root=root, config=MathEduConfig())
    assert r.skill_dir("math_qa") == os.path.join(root, "skills", "math_qa")
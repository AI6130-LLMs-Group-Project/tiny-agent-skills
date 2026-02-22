import argparse
import os
import sys
from typing import List

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.models import MathEduConfig
from core.runner import MathEduRunner
from math_tools import registry as math_tools_registry


def _positive_int(value: str) -> int:
    iv = int(value)
    if iv <= 0:
        raise argparse.ArgumentTypeError("--max-steps must be > 0")
    return iv


def _available_skills(project_root: str) -> List[str]:
    skills_dir = os.path.join(project_root, "skills")
    if not os.path.isdir(skills_dir):
        return []
    names: List[str] = []
    for name in os.listdir(skills_dir):
        full = os.path.join(skills_dir, name)
        if os.path.isdir(full) and os.path.isfile(os.path.join(full, "SKILL.md")):
            names.append(name)
    return sorted(names)


def main() -> None:
    skills = _available_skills(REPO_ROOT)

    parser = argparse.ArgumentParser(description="Run Tiny Agent Skills v2 for math education")
    parser.add_argument("--skill", choices=skills)
    parser.add_argument("--task")
    parser.add_argument("--task-file")
    parser.add_argument("--output-file")
    parser.add_argument("--base-url", default="http://127.0.0.1:1234")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--max-steps", type=_positive_int, default=10)
    parser.add_argument("--stop-on-answer", action="store_true", help="Stop early when answer detected")
    parser.add_argument("--list-skills", action="store_true")
    parser.add_argument("--list-tools", action="store_true")
    args = parser.parse_args()

    if args.list_skills:
        print("Available skills:")
        for s in skills:
            print(f"  - {s}")
        return

    if args.list_tools:
        print("Available tools:")
        for t in math_tools_registry.list():
            print(f"  - {t.name}: {t.description}")
        return

    if not args.skill:
        parser.error("--skill is required (or use --list-skills)")

    task_text = (args.task or "").strip()
    if args.task_file:
        try:
            with open(args.task_file, "r", encoding="utf-8") as f:
                task_text = f.read().strip()
        except Exception as exc:
            parser.error(f"failed to read --task-file: {exc}")

    if not task_text:
        parser.error("task is empty: use --task or --task-file")

    os.environ.setdefault("SKILL_STEP_LOG", "1")
    os.environ.setdefault("SKILL_MAX_HISTORY_STEPS", "12")
    os.environ.setdefault("SKILL_MAX_HISTORY_CHARS", "1800")

    config = MathEduConfig(
        base_url=args.base_url,
        model=args.model,
        max_steps=args.max_steps,
        stop_on_answer=args.stop_on_answer,
    )
    runner = MathEduRunner(project_root=REPO_ROOT, config=config)
    try:
        result = runner.run(task=task_text, skill_name=args.skill, tools_registry=math_tools_registry)
    except KeyboardInterrupt:
        print("Interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"ERROR: runner failed: {exc}")
        sys.exit(1)

    lines = []
    lines.append("=" * 80)
    lines.append(f"Skill: {args.skill}")
    lines.append(f"Task: {task_text}")
    lines.append("=" * 80)

    for step in result.get("steps", []):
        lines.append(f"Step {step.get('step')}")
        lines.append(f"  Subskill: {step.get('subskill')}")
        lines.append(f"  OrchestratorOutput: {step.get('orchestrator_output', '')}")
        lines.append(f"  SubskillOutput: {step.get('subskill_output', '')}")
        if step.get("tool_call"):
            lines.append(f"  ToolCall: {step.get('tool_call')}")
        if step.get("tool_result") is not None:
            lines.append(f"  ToolResult: {step.get('tool_result')}")
        if step.get("tool_error"):
            lines.append(f"  ToolError: {step.get('tool_error')}")
        lines.append("")

    if result.get("final_answer") is not None:
        lines.append("FinalAnswer:")
        lines.append(str(result["final_answer"]))
    if result.get("diagnosis") is not None:
        lines.append("Diagnosis:")
        lines.append(str(result["diagnosis"]))

    text = "\n".join(lines)
    print(text)

    if args.output_file:
        out_dir = os.path.dirname(args.output_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()

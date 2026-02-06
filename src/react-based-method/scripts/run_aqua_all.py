import json
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from run_skill import run_skill


def _print_step_log(step: dict) -> None:
    print(f"  Step {step.get('step', '')}")
    print(f"    Subskill: {step.get('subskill', '')}")
    print(f"    OrchestratorOutput: {step.get('orchestrator_output', '')}")
    print(f"    SubskillOutput: {step.get('subskill_output', '')}")
    if step.get("tool_call"):
        print(f"    ToolCall: {json.dumps(step.get('tool_call'), ensure_ascii=True)}")
    if step.get("tool_result") is not None:
        print(f"    ToolResult: {json.dumps(step.get('tool_result'), ensure_ascii=True)}")
    if step.get("tool_error"):
        print(f"    ToolError: {step.get('tool_error')}")


def _extract_answer_text(steps: list[dict]) -> str:
    for step in reversed(steps):
        text = step.get("subskill_output", "") or ""
        lower = text.lower()
        idx = lower.rfind("answer[")
        if idx >= 0:
            segment = text[idx + len("answer[") :]
            end = segment.find("]")
            if end >= 0:
                return segment[:end].strip()
            return segment.strip()
    return ""


def _extract_label(text: str) -> str:
    if not text:
        return ""
    # Prefer a single-letter label if present.
    m = re.search(r"\b([A-E])\b", text.upper())
    if m:
        return m.group(1)
    # Fall back to leading label formats like "A)" or "A.".
    m = re.search(r"([A-E])\s*[\)\.]", text.upper())
    if m:
        return m.group(1)
    return ""


def _format_input(question: str, options: list[str]) -> str:
    lines = ["Question: " + question, "Options:"]
    for opt in options:
        lines.append(opt)
    lines.append("Answer with the best option letter: A, B, C, D, or E.")
    return "\n".join(lines)


def main() -> None:
    os.environ["SKILL_STEP_LOG"] = "1"
    os.environ["SKILL_MAX_HISTORY_STEPS"] = "12"
    os.environ["SKILL_MAX_HISTORY_CHARS"] = "1800"
    data_path = "data/ps/AQuA/AQuA.json"
    out_path = "aqua_math_solver_outputs.jsonl"

    correct = 0
    total = 0
    with open(data_path, "r", encoding="utf-8") as f_in, open(out_path, "w", encoding="utf-8") as f_out:
        for i, line in enumerate(f_in):
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            task = _format_input(ex["question"], ex["options"])
            result = run_skill(
                task=task,
                skill_dir="skills/math_solver",
                base_url="http://127.0.0.1:1234",
                model="local-model",
                max_steps=10,
                stop_subskill="verify",
                stop_on_answer=True,
            )
            answer_text = _extract_answer_text(result["steps"])
            pred_label = _extract_label(answer_text)
            gold_label = (ex.get("correct") or "").strip().upper()
            is_correct = pred_label == gold_label and pred_label != ""

            total += 1
            if is_correct:
                correct += 1
            acc = correct / total

            record = {
                "idx": i,
                "question": ex["question"],
                "options": ex["options"],
                "gold_label": gold_label,
                "pred_label": pred_label,
                "answer_text": answer_text,
                "steps": result["steps"],
            }
            f_out.write(json.dumps(record, ensure_ascii=True) + "\n")

            print(f"Example {i}")
            print(f"  Question: {ex['question']}")
            print(f"  Options: {ex['options']}")
            print(f"  ExpectedLabel: {gold_label}")
            for step in result["steps"]:
                _print_step_log(step)
            print(f"  PredictedAnswerText: {answer_text if answer_text else '<missing>'}")
            print(f"  PredictedLabel: {pred_label if pred_label else '<missing>'}")
            print(f"  Correct: {is_correct}")
            print(f"  Accuracy: {correct}/{total} = {acc:.4f}")
            print()

    print("wrote", out_path)


if __name__ == "__main__":
    main()

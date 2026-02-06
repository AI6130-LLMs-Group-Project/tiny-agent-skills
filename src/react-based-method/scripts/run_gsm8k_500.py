import json
import os
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

def _extract_answer(steps: list[dict]) -> str:
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


def _parse_float(s: str) -> float | None:
    if not s:
        return None
    s = s.replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def main() -> None:
    os.environ["SKILL_STEP_LOG"] = "1"
    os.environ["SKILL_MAX_HISTORY_STEPS"] = "12"
    os.environ["SKILL_MAX_HISTORY_CHARS"] = "1800"
    # data = json.load(open('data/ps/gsm8k/gsm8k.json'))[:500]
    data = json.load(open('data/ps/gsm8k/gsm8kdouble.json', encoding='utf-8'))
    out_path = 'gsm8k_math_solver_outputs.jsonl'

    with open(out_path, 'w', encoding='utf-8') as f:
        correct = 0
        for i, ex in enumerate(data):
            result = run_skill(
                task=ex['question'],
                skill_dir='skills/math_solver',
                base_url='http://127.0.0.1:1234',
                model='local-model',
                max_steps=10,
                stop_subskill="verify",
                stop_on_answer=True,
            )
            record = {
                "idx": i,
                "question": ex["question"],
                "gold_answer": ex["answer"],
                "steps": result["steps"],
            }
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

            print(f"Example {i}")
            print(f"  Question: {ex['question']}")
            print(f"  ExpectedAnswer: {ex['answer']}")
            for step in result["steps"]:
                _print_step_log(step)
            pred = _extract_answer(result["steps"])
            pred_f = _parse_float(pred)
            gold_f = _parse_float(str(ex["answer"]))
            is_correct = False
            if pred_f is not None and gold_f is not None:
                is_correct = abs(pred_f - gold_f) <= 1e-6
            correct += 1 if is_correct else 0
            acc = correct / (i + 1)
            print(f"  PredictedAnswer: {pred if pred else '<missing>'}")
            print(f"  Correct: {is_correct}")
            print(f"  Accuracy: {correct}/{i+1} = {acc:.4f}")
            print()

    print("wrote", out_path)


if __name__ == "__main__":
    main()

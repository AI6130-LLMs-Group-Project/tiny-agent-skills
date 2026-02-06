#!/usr/bin/env python3
import argparse
import importlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from tool_registry import ToolRegistry, parse_tool_args


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_rules(skill_dir: str) -> Dict[str, str]:
    rules_dir = os.path.join(skill_dir, "rules")
    rules = {}
    if os.path.isdir(rules_dir):
        for name in sorted(os.listdir(rules_dir)):
            if not name.endswith(".md"):
                continue
            key = os.path.splitext(name)[0]
            rules[key] = read_text(os.path.join(rules_dir, name))
    rules["skill"] = read_text(os.path.join(skill_dir, "SKILL.md"))
    return rules


def http_json(url: str, payload: Optional[dict] = None, timeout: int = 300) -> dict:
    if payload is None:
        req = Request(url, method="GET")
    else:
        body = json.dumps(payload).encode("utf-8")
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            detail = ""
        raise RuntimeError(f"HTTP {e.code} error from {url}: {detail}") from e


def chat_completion(base_url: str, model: str, messages: List[dict], tools: Optional[List[dict]] = None) -> dict:
    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    return http_json(url, payload=payload, timeout=300)


def parse_subskill(text: str, subskills: List[str]) -> str:
    pattern = r"subskill\s*[:\-]\s*([a-zA-Z0-9_\-]+)"
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if m:
        name = m.group(1).lower().replace(".md", "")
        if name in {"answer", "compute", "extract", "plan"}:
            if name == "answer" and "verify" in subskills:
                return "verify"
            if name == "compute" and "calculate" in subskills:
                return "calculate"
            if name in {"extract", "plan"} and name in subskills:
                return name
        if name in subskills:
            return name
    lowered = text.lower()
    if "answer" in lowered and "verify" in subskills:
        return "verify"
    if "compute" in lowered and "calculate" in subskills:
        return "calculate"
    for name in subskills:
        if name in lowered:
            return name
    raise ValueError(f"Could not parse Subskill from LLM output:\n{text}")


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _trim_history(history: List[dict]) -> List[dict]:
    max_steps = int(os.environ.get("SKILL_MAX_HISTORY_STEPS", "6"))
    return history[-max_steps:] if max_steps > 0 else history


def build_orchestrator_messages(
    task: str,
    rules: dict[str, str],
    subskills: list[str],
    history: list[dict],
    max_history_steps: int,
    max_history_chars: int,
) -> list[dict]:
    system = (
        "You are the main skill orchestrator. Use ONLY the main skill instructions below. "
        "Decide which subskill should be applied next.\n"
        "**[CRITICAL LANGUAGE RULE]**: You MUST reason in the SAME language as the user's input question. "
        "If the input is in Chinese, ALL your reasoning and output MUST be in Chinese. "
        "If the input is in English, use English.\n"
        "**[关键语言规则]**: 你必须使用与用户输入问题相同的语言进行推理。"
        "如果输入是中文,你的所有推理和输出必须使用中文。如果输入是英文,则使用英文。\n\n"
        f"Output exactly one line in the format: Subskill: <{'|'.join(subskills)}>\n\n"
        + rules["skill"]
    )
    max_chars = max_history_chars
    user_lines = [f"Input: {task}"]
    trimmed = _trim_history(history)
    if trimmed:
        user_lines.append("History:")
        for i, h in enumerate(trimmed, 1):
            user_lines.append(f"Step {i}")
            user_lines.append(f"Subskill: {h.get('subskill','')}")
            sub_out = _truncate_text(h.get('subskill_output','') or "", max_chars)
            orch_out = _truncate_text(h.get('orchestrator_output','') or "", max_chars)
            user_lines.append(f"SubskillOutput: {sub_out}")
            user_lines.append(f"OrchestratorOutput: {orch_out}")
            if h.get("tool_call"):
                user_lines.append(f"ToolCall: {_truncate_text(str(h['tool_call']), max_chars)}")
            if h.get("tool_result"):
                user_lines.append(f"ToolResult: {_truncate_text(str(h['tool_result']), max_chars)}")
    user_lines.append("Choose the next subskill.")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_lines)},
    ]

def detect_language(text: str) -> str:
    """检测文本是中文还是英文"""
    if not text:
        return "english"
    chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len(text)
    return "chinese" if chinese_count > total_chars * 0.3 else "english"


def build_subskill_messages(
    task: str,
    rules: dict[str, str],
    subskill: str,
    history: list[dict],
    max_history_steps: int,
    max_history_chars: int,
) -> list[dict]:
    rule_text = rules.get(subskill, "")
    
    # 检测任务语言
    task_lang = detect_language(task)
    lang_name = "Chinese" if task_lang == "chinese" else "English"
    lang_name_cn = "中文" if task_lang == "chinese" else "英文"
    
    system = (
        "You are executing a skill subtask. Follow the subskill instructions below. "
        "If you need a tool, call it in the correct format. Otherwise respond with the required output format.\n"
        f"**[DETECTED INPUT LANGUAGE: {lang_name}]**\n"
        f"**YOU MUST RESPOND ONLY IN {lang_name.upper()}.**\n"
        f"Do NOT use English if input is Chinese. Do NOT use Chinese if input is English.\n\n"
        "**[CRITICAL LANGUAGE RULE - TOP PRIORITY]**: You MUST use the SAME language as the user's original question for ALL outputs. "
        "If it's Chinese, your Thought, Action, and Observation MUST be in Chinese. "
        "If it's English, use English. This rule overrides everything else.\n"
        "**[关键语言规则 - 最高优先级]**: 你必须使用与用户原始问题相同的语言输出所有内容。"
        f"输入语言已检测为: {lang_name_cn}\n"
        f"**你必须只用{lang_name_cn}回复,不要混合使用两种语言。**\n\n"
        + rules["skill"]
        + ("\n\n" + rule_text if rule_text else "")
    )
    max_chars = max_history_chars
    user_lines = [
        f"**IMPORTANT: Input language is {lang_name}. You MUST respond in {lang_name} ONLY.**\n",
        f"Input: {task}"
    ]
    trimmed = _trim_history(history)
    if trimmed:
        user_lines.append("History:")
        for i, h in enumerate(trimmed, 1):
            user_lines.append(f"Step {i}")
            user_lines.append(f"Subskill: {h.get('subskill','')}")
            sub_out = _truncate_text(h.get('subskill_output','') or "", max_chars)
            orch_out = _truncate_text(h.get('orchestrator_output','') or "", max_chars)
            user_lines.append(f"SubskillOutput: {sub_out}")
            user_lines.append(f"OrchestratorOutput: {orch_out}")
            if h.get("tool_call"):
                user_lines.append(f"ToolCall: {_truncate_text(str(h['tool_call']), max_chars)}")
            if h.get("tool_result"):
                user_lines.append(f"ToolResult: {_truncate_text(str(h['tool_result']), max_chars)}")
    user_lines.append(f"**Remember: Respond ONLY in {lang_name}. Do NOT switch languages.**")
    user_lines.append("Provide the next output.")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_lines)},
    ]


def extract_assistant_content(resp: dict) -> str:
    return resp["choices"][0]["message"].get("content", "") or ""


def extract_tool_calls(resp: dict) -> List[dict]:
    msg = resp["choices"][0]["message"]
    return msg.get("tool_calls", []) or []


def run_skill(
    task: str,
    skill_dir: str,
    base_url: str,
    model: str,
    tools_registry: Optional[ToolRegistry] = None,
    max_steps: int = 10,
    stop_subskill: str = "finish",
    stop_on_answer: bool = True,
) -> dict:
    rules = load_rules(skill_dir)
    subskills = [k for k in rules.keys() if k != "skill"]
    history: List[Dict[str, Any]] = []
    log_steps = os.environ.get("SKILL_STEP_LOG") == "1"
    
    # 添加这两行获取环境变量
    max_history_steps = int(os.environ.get("SKILL_MAX_HISTORY_STEPS", "12"))
    max_history_chars = int(os.environ.get("SKILL_MAX_HISTORY_CHARS", "1800"))

    if tools_registry and hasattr(tools_registry, "reset"):
        try:
            tools_registry.reset()
        except Exception:
            pass

    for step in range(max_steps):
        # 修正这一行，添加缺少的参数
        orch_messages = build_orchestrator_messages(
            task, rules, subskills, history, max_history_steps, max_history_chars
        )
        orch_resp = chat_completion(base_url, model, orch_messages)
        orch_output = extract_assistant_content(orch_resp)
        subskill = parse_subskill(orch_output, subskills)

        # 修正这一行，添加缺少的参数
        sub_messages = build_subskill_messages(
            task, rules, subskill, history, max_history_steps, max_history_chars
        )
        tool_defs = tools_registry.openai_tools() if tools_registry else None
        sub_resp = chat_completion(base_url, model, sub_messages, tools=tool_defs)
        sub_output = extract_assistant_content(sub_resp)
        tool_calls = extract_tool_calls(sub_resp)

        step_record: Dict[str, Any] = {
            "step": step + 1,
            "subskill": subskill,
            "orchestrator_output": orch_output,
            "subskill_output": sub_output,
        }

        if tool_calls and tools_registry:
            call = tool_calls[0]
            fn = call.get("function", {})
            name = fn.get("name")
            arg_str = fn.get("arguments", "")
            args = parse_tool_args(arg_str)
            tool = tools_registry.get(name)
            if tool is None:
                step_record["tool_call"] = {"name": name, "arguments": args}
                step_record["tool_error"] = f"Unknown tool: {name}"
            else:
                result = tool.func(**args)
                step_record["tool_call"] = {"name": name, "arguments": args}
                step_record["tool_result"] = result
        history.append(step_record)
        if log_steps:
            print(f"Step {step_record['step']}")
            print("OrchestratorOutput:", step_record.get("orchestrator_output", ""))
            print("SubskillOutput:", step_record.get("subskill_output", ""))
            if step_record.get("tool_call"):
                print("ToolCall:", step_record["tool_call"])
            if step_record.get("tool_result") is not None:
                print("ToolResult:", step_record.get("tool_result"))
            if step_record.get("tool_error"):
                print("ToolError:", step_record.get("tool_error"))
            print()

        if stop_on_answer and "answer[" in (sub_output or "").lower() and not tool_calls:
            break
        if subskill == stop_subskill and not tool_calls:
            break

    return {
        "input": task,
        "skill_dir": skill_dir,
        "steps": history,
    }


def load_tools_module(module_path: str) -> Optional[ToolRegistry]:
    if not module_path:
        return None
    mod = importlib.import_module(module_path)
    if hasattr(mod, "get_tool_registry"):
        return mod.get_tool_registry()
    if hasattr(mod, "registry"):
        return mod.registry
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generic skill runner")
    parser.add_argument("--skill", required=True, help="Skill folder name or path")
    parser.add_argument("--input", required=True, help="Input to the skill")
    parser.add_argument("--base-url", default="http://127.0.0.1:1234")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--tools", default="", help="Python module path for tools, e.g. tools")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--stop-subskill", default="finish")
    parser.add_argument("--json", default="", help="Write JSON log to file (default: stdout)")
    args = parser.parse_args()

    skill_dir = args.skill
    if not os.path.isabs(skill_dir):
        skill_dir = os.path.join(os.getcwd(), skill_dir)

    tools_registry = load_tools_module(args.tools)

    result = run_skill(
        task=args.input,
        skill_dir=skill_dir,
        base_url=args.base_url,
        model=args.model,
        tools_registry=tools_registry,
        max_steps=args.max_steps,
        stop_subskill=args.stop_subskill,
    )

    output = json.dumps(result, ensure_ascii=True, indent=2)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

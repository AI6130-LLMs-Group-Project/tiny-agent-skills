import argparse
import json
import os
import random
import re
import sys
import time

import wrappers
import wikienv

ROOT = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(ROOT, "skills", "fever")
if ROOT not in sys.path:
    sys.path.append(ROOT)

import tools as fever_tools
import run_skill


def parse_finish_label(steps):
    for step in reversed(steps):
        text = step.get("subskill_output", "")
        m = re.search(r"finish\[(SUPPORTS|REFUTES|NOT ENOUGH INFO)\]", text, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return "NOT ENOUGH INFO"


def print_steps(steps):
    for step in steps:
        print(f"Step {step.get('step')}")
        print("OrchestratorOutput:", step.get("orchestrator_output", ""))
        print("SubskillOutput:", step.get("subskill_output", ""))
        if step.get("tool_call"):
            print("ToolCall:", step.get("tool_call"))
            tool_args = step["tool_call"].get("arguments", {})
            print("ToolParameters:", tool_args)
        if step.get("tool_result") is not None:
            print("ToolResult:", step.get("tool_result"))
        if step.get("tool_error"):
            print("ToolError:", step.get("tool_error"))
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:1234")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--split", default="dev", choices=["dev", "test", "train"])
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--seed", type=int, default=233)
    parser.add_argument("--max-steps", type=int, default=7)
    parser.add_argument("--skill-dir", default=SKILL_DIR)
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args()

    env = wikienv.WikiEnv()
    env = wrappers.FeverWrapper(env, split=args.split, data_dir=args.data_dir)
    env = wrappers.LoggingWrapper(env)

    idxs = list(range(7405))
    random.Random(233).shuffle(idxs)

    rs = []
    old_time = time.time()
    for i in idxs[: args.n]:
        claim = env.reset(i)
        gold = env.gold()
        result = run_skill.run_skill(
            task=claim,
            skill_dir=args.skill_dir,
            base_url=args.base_url,
            model=args.model,
            tools_registry=fever_tools.registry,
            max_steps=args.max_steps,
            stop_subskill="finish",
        )
        pred = parse_finish_label(result["steps"])
        em = 1 if pred == gold else 0
        print(f"Claim: {claim}")
        print_steps(result["steps"])
        print(f"Expected: {gold}")
        print(f"Actual: {pred}")
        print()
        rs.append(em)
        print(sum(rs), len(rs), sum(rs) / len(rs), (time.time() - old_time) / len(rs))
        print("-----------")
        print()


if __name__ == "__main__":
    main()

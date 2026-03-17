import os
import sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from run_skill import run_skill

os.environ["SKILL_STEP_LOG"] = "1"

port = os.environ.get("LLM_PORT", "1025")
base_url = f"http://127.0.0.1:{port}"

# 测试用例列表
test_cases = [
    {
        "name": "中文事实验证 - 支持",
        "claim": "爱因斯坦在1921年获得了诺贝尔物理学奖。",
        "expected": "SUPPORTS"
    },
    {
        "name": "中文事实验证 - 反驳",
        "claim": "习近平在2000年是中国的国家主席。",
        "expected": "REFUTES"
    },
    {
        "name": "中文事实验证 - 信息不足",
        "claim": "张三获得了2023年国际象棋冠军。",
        "expected": "NOT ENOUGH INFO"
    },
    {
        "name": "English fact verification - Support",
        "claim": "Python was created by Guido van Rossum.",
        "expected": "SUPPORTS"
    },
    {
        "name": "English fact verification - Refute",
        "claim": "The Pacific Ocean is the smallest ocean.",
        "expected": "REFUTES"
    }
]

def run_test(test_case):
    """运行单个测试用例"""
    print(f"\n{'='*70}")
    print(f"Test: {test_case['name']}")
    print(f"Claim: {test_case['claim']}")
    print(f"Expected: {test_case['expected']}")
    print(f"{'='*70}\n")
    
    result = run_skill(
        task=test_case['claim'],
        skill_dir='skills/fever',
        base_url=base_url,
        model='local-model',
        max_steps=10,
        stop_subskill="finish",
        stop_on_answer=True,
    )
    
    print(f"\n{'='*70}")
    print("Step-by-Step Reasoning:")
    print(f"{'='*70}")
    
    for step in result["steps"]:
        print(f"\nStep {step['step']}")
        print(f"Subskill: {step['subskill']}")
        print(f"Output: {step['subskill_output']}")
        if step.get("tool_call"):
            print(f"Tool Call: {step['tool_call']}")
        if step.get("tool_result"):
            print(f"Tool Result: {step['tool_result']}")
    
    # 提取最终答案
    last_step = result["steps"][-1] if result["steps"] else {}
    output = last_step.get("subskill_output", "")
    
    # 判断答案
    answer = "UNKNOWN"
    if "SUPPORTS" in output.upper():
        answer = "SUPPORTS"
    elif "REFUTES" in output.upper():
        answer = "REFUTES"
    elif "NOT ENOUGH INFO" in output.upper():
        answer = "NOT ENOUGH INFO"
    
    print(f"\n{'='*70}")
    print(f"Actual Result: {answer}")
    print(f"Expected: {test_case['expected']}")
    
    if answer == test_case['expected']:
        print("✅ PASS")
        return True
    else:
        print("❌ FAIL")
        return False

def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("FEVER Fact Verification Skill Tests (English & Chinese)")
    print("事实验证技能测试(英文和中文)")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        try:
            if run_test(test_case):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            failed += 1
    
    print(f"\n{'='*70}")
    print(f"Test Summary: {passed} passed, {failed} failed")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()

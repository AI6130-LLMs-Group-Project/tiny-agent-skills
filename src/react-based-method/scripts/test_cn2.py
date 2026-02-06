import os
import sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from run_skill import run_skill

os.environ["SKILL_STEP_LOG"] = "1"

# 测试用例列表
test_cases = [
    {
        "name": "中文数学 - 简单加减法",
        "task": "小明有12个苹果,他吃掉了3个,又买了5个。他现在有多少个苹果?",
        "expected_answer": "14"
    },
    {
        "name": "中文数学 - 百分比计算",
        "task": "一件商品原价为200元,打8折后价格是多少?",
        "expected_answer": "160"
    },
    {
        "name": "中文数学 - 多步计算",
        "task": "小王有500元,他花了40%买书,又花了50元买笔。他还剩多少钱?",
        "expected_answer": "250"
    },
    {
        "name": "English Math - Simple Addition",
        "task": "John has 15 apples. He receives 8 more apples. How many apples does John have now?",
        "expected_answer": "23"
    },
    {
        "name": "English Math - Percentage Calculation",
        "task": "A product costs $100. What is the price after a 20% discount?",
        "expected_answer": "80"
    },
    {
        "name": "中文数学 - 长方形面积",
        "task": "一个长方形长8米,宽5米,求面积。",
        "expected_answer": "40"
    },
]

def run_test(test_case):
    """运行单个测试用例"""
    print(f"\n{'='*70}")
    print(f"Test: {test_case['name']}")
    print(f"Task: {test_case['task']}")
    print(f"Expected Answer: {test_case['expected_answer']}")
    print(f"{'='*70}\n")
    
    result = run_skill(
        task=test_case['task'],
        skill_dir="skills/math_solver",
        base_url="http://127.0.0.1:1234",
        model="local-model",
        max_steps=10,
        stop_subskill="verify",
    )
    
    print(f"\n{'='*70}")
    print("Step-by-Step Reasoning (推理步骤):")
    print(f"{'='*70}")
    
    for step in result["steps"]:
        print(f"\nStep {step['step']}")
        print(f"Subskill: {step['subskill']}")
        # 截断长输出以便阅读
        output = step['subskill_output']
        if len(output) > 300:
            print(f"Output: {output[:300]}...")
        else:
            print(f"Output: {output}")
    
    # 提取最终答案
    last_step = result["steps"][-1] if result["steps"] else {}
    output = last_step.get("subskill_output", "")
    
    # 简单的答案提取逻辑
    answer = None
    if "answer[" in output.lower():
        # 提取 answer[...] 中的内容
        start = output.lower().find("answer[") + 7
        end = output.find("]", start)
        if end > start:
            answer = output[start:end].strip()
    
    # 检查是否为中文输出
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in output)
    language = "Chinese" if has_chinese else "English"
    
    print(f"\n{'='*70}")
    print(f"Final Answer: {answer}")
    print(f"Expected: {test_case['expected_answer']}")
    print(f"Language: {language}")
    
    # 验证答案(允许一定的模糊匹配)
    if answer:
        # 移除单位和符号进行比较
        answer_num = ''.join(filter(str.isdigit, answer))
        expected_num = ''.join(filter(str.isdigit, test_case['expected_answer']))
        
        if answer_num == expected_num:
            print("✅ PASS")
            return True, language
        else:
            print(f"❌ FAIL - Answer mismatch")
            return False, language
    else:
        print("❌ FAIL - No answer found")
        return False, language

def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("Math Solver Skill Tests (English & Chinese)")
    print("数学求解技能测试(英文和中文)")
    print("="*70)
    
    passed = 0
    failed = 0
    chinese_count = 0
    english_count = 0
    
    for test_case in test_cases:
        try:
            success, language = run_test(test_case)
            if success:
                passed += 1
            else:
                failed += 1
            
            if language == "Chinese":
                chinese_count += 1
            else:
                english_count += 1
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*70}")
    print("Test Summary:")
    print(f"{'='*70}")
    print(f"Total: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Chinese Output: {chinese_count}")
    print(f"English Output: {english_count}")
    print(f"{'='*70}\n")
    
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print(f"⚠️  {failed} test(s) failed")

if __name__ == "__main__":
    main()
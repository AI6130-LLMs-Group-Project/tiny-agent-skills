# Skill: math_qa

目标：解答数学题，并给出可检查的步骤。

## 子技能
1. understand
2. plan
3. solve
4. verify

## 流程（严格）
- 必须按顺序执行：understand -> plan -> solve -> verify
- `verify` 后立即停止
- 禁止回退到前序子技能，除非工具报错且无法继续

## 全局输出约束
- 禁止输出 `answer[...]`、`answer:`、`final[...]` 这类占位符
- 仅 `verify` 可给最终答案，格式必须为：
  - `FINAL_ANSWER: <答案>`
- 其他子技能不得给最终答案

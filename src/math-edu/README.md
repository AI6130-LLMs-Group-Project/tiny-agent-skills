# Tiny Agent Skills v2（数学教育智能体）

Tiny Agent Skills v2 for math education with three core skills:

面向数学教育场景的 Tiny Agent Skills v2，包含三类核心能力：

1. `math_qa`：数学题目解答 / Math question answering
2. `math_diagnosis`：学习成果检测与薄弱点定位 / Learning diagnosis and gap analysis
3. `math_tutoring`：分步讲解与练习辅导 / Step-by-step tutoring and practice

---

## 项目结构 | Project Structure

- `core/`：运行配置与统一 Runner / shared config and runner
- `skills/`：三类技能定义（`SKILL.md` + `rules/*.md`）/ skill definitions
- `math_tools.py`：安全数学计算工具 / safe math tool
- `tool_registry.py`：工具注册与解析 / tool registry
- `run_math_edu_skill.py`：统一命令行入口 / unified CLI entry
- `inputs/`：示例输入文件 / input templates
- `outputs/`：运行输出文件 / run outputs
- `.vscode/launch.json`：VS Code 一键运行配置 / one-click debug configs

---

## 环境准备 | Setup

### 中文

1. 建议使用 Python 3.10+。
2. 在项目根目录执行。
3. 若有依赖文件，先安装依赖。

### English

1. Use Python 3.10+ (recommended).
2. Run all commands from the project root (`tiny_agent_skills_v2`).
3. If this repository has `requirements.txt`, install dependencies first.
4. Ensure your LLM backend is reachable through `--base-url` and accepts the model name from `--model`.
5. Prepare `inputs/*.txt` before running each skill, or pass text directly with `--task`.

```bash
# Optional
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# If requirements.txt exists
pip install -r requirements.txt
```

---

## 命令行参数 | CLI Arguments

```bash
python run_math_edu_skill.py [OPTIONS]
```

常用参数 / Common options:

- `--skill {math_qa,math_diagnosis,math_tutoring}`：选择技能 / choose skill
- `--task "..."`：直接传入任务文本 / inline task
- `--task-file path`：从文件读取任务 / read task from file
- `--output-file path`：将结果写入文件 / save result to file
- `--base-url URL`：模型服务地址 / model service URL
- `--model NAME`：模型名称 / model name
- `--max-steps N`：最大推理步数 / max steps
- `--list-skills`：查看可用技能 / list skills
- `--list-tools`：查看可用工具 / list tools

English notes:

- `--task` and `--task-file` are mutually practical alternatives; if both are provided, file content is typically used as the final task text in this project flow.
- `--output-file` is strongly recommended for reproducibility because it preserves full step logs and final outputs.
- `--max-steps` controls reasoning depth; increase it when tasks need longer decomposition.
- `--list-skills` and `--list-tools` are useful sanity checks before your first run.

---

## 先检查可用项 | Check Available Skills/Tools

```bash
python run_math_edu_skill.py --list-skills
python run_math_edu_skill.py --list-tools
```

---

## 三类功能运行示例 | How to Run the Three Features

### 1) 题目解答（`math_qa`）| Question Answering

```bash
python run_math_edu_skill.py \
	--skill math_qa \
	--task-file ./inputs/qa_task.txt \
	--output-file ./outputs/qa_result.txt
```

### 2) 学习检测（`math_diagnosis`）| Learning Diagnosis

```bash
python run_math_edu_skill.py \
	--skill math_diagnosis \
	--task-file ./inputs/diagnosis_task.txt \
	--output-file ./outputs/diagnosis_result.txt
```

### 3) 补习辅导（`math_tutoring`）| Tutoring

```bash
python run_math_edu_skill.py \
	--skill math_tutoring \
	--task-file ./inputs/tutoring_task.txt \
	--output-file ./outputs/tutoring_result.txt
```

> 若不使用 `--task-file`，也可用 `--task "..."` 直接输入。
>
> You can use `--task "..."` directly if you do not want `--task-file`.

### English step-by-step walkthrough

1. Create or edit one input file in `inputs/`.
2. Choose one skill based on your objective:
	- `math_qa`: solve a math problem with reasoning
	- `math_diagnosis`: evaluate student performance and identify knowledge gaps
	- `math_tutoring`: provide guided teaching with progressive practice
3. Run the corresponding command with `--output-file`.
4. Open the output file in `outputs/` and review:
	- intermediate `steps`
	- `final_answer` for QA/tutoring tasks
	- `diagnosis` for assessment tasks
5. Iterate by refining input prompts (difficulty, grade level, expected format).

Windows PowerShell one-line commands:

```powershell
python .\run_math_edu_skill.py --skill math_qa --task-file .\inputs\qa_task.txt --output-file .\outputs\qa_result.txt
python .\run_math_edu_skill.py --skill math_diagnosis --task-file .\inputs\diagnosis_task.txt --output-file .\outputs\diagnosis_result.txt
python .\run_math_edu_skill.py --skill math_tutoring --task-file .\inputs\tutoring_task.txt --output-file .\outputs\tutoring_result.txt
```

---

## 输入模板建议 | Suggested Input Templates

### `inputs/qa_task.txt`

```text
题目：解方程 2x + 3 = 11，并说明每一步依据。
```

English sample:

```text
Problem: Solve 2x + 3 = 11 and explain each transformation step.
Output format: show steps first, then final answer on a separate line.
```

### `inputs/diagnosis_task.txt`

```text
题目：解方程 2x + 3 = 11
学生答案：x = 5
学生步骤：2x = 11 - 3 = 8，所以 x = 5
请判断是否正确，定位错误知识点，并给出补救练习建议。
```

English sample:

```text
Question: Solve 2x + 3 = 11
Student answer: x = 5
Student steps: 2x = 11 - 3 = 8, therefore x = 5
Please evaluate correctness, identify misconception type, and suggest remedial exercises.
```

### `inputs/tutoring_task.txt`

```text
我不会一元一次方程，请从基础概念开始讲解，并给两道由易到难练习题。
```

English sample:

```text
I struggle with linear equations in one variable.
Please teach from fundamentals and provide two graded practice questions.
```

---

## VS Code 一键运行 | One-click Run in VS Code

### 中文

1. 打开左侧「运行和调试」。
2. 选择 `Math QA` / `Math Diagnosis` / `Math Tutoring`。
3. 点击绿色运行按钮。
4. 查看 `outputs/*.txt`。

### English

1. Open **Run and Debug** in VS Code.
2. Choose `Math QA`, `Math Diagnosis`, or `Math Tutoring`.
3. Click the green run button.
4. Wait for terminal completion and check output files under `outputs/`.
5. If a run fails, inspect the integrated terminal first, then validate input file paths.

---

## 输出说明 | Output Notes

运行结果通常包含：

- `steps`：中间推理步骤 / intermediate steps
- `final_answer`：最终答案（常见于 `math_qa`）/ final answer
- `diagnosis`：诊断报告（常见于 `math_diagnosis`）/ diagnosis report

---

## 常见问题 | FAQ

### 1) `--skill is required` 报错

- 原因：未提供 `--skill`。
- 解决：使用 `--skill math_qa`（或另外两种）。

### 2) `task is empty` 报错

- 原因：`--task` 为空，或 `--task-file` 文件内容为空。
- 解决：检查输入文件内容。

### 3) 找不到技能目录 / `SKILL.md`

- 原因：目录结构不完整。
- 解决：确认 `skills/<skill_name>/SKILL.md` 存在。

### 4) 运行失败（Exit Code 1）

- 先检查模型服务地址与模型名（`--base-url`、`--model`）。
- 再检查 `inputs/` 文件是否存在且非空。

### English FAQ

#### 1) Error: `--skill is required`

- Cause: You launched without selecting a skill.
- Fix: Add `--skill math_qa` (or `math_diagnosis` / `math_tutoring`).

#### 2) Error: `task is empty`

- Cause: Empty `--task`, or `--task-file` points to an empty file.
- Fix: Fill the input text file with actual task content.

#### 3) Error: skill directory or `SKILL.md` not found

- Cause: Missing or broken folder structure under `skills/`.
- Fix: Ensure `skills/<skill_name>/SKILL.md` exists.

#### 4) Exit Code 1 after command execution

- Check model endpoint (`--base-url`) and model identifier (`--model`).
- Check that input files exist and are readable.
- Re-run with `--list-skills` and `--list-tools` to confirm environment consistency.

#### 5) Output does not include expected diagnosis/answer

- Some tasks may require clearer prompt constraints.
- Add explicit instructions in input text, such as:
	- "Return diagnosis with misconception category and confidence"
	- "Return final answer in one dedicated line"

---

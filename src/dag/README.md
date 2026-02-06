# DAG（Pipeline）框架

基于**有向无环图**的事实核查 pipeline：由配置决定步骤顺序，每步一个 skill，小模型只在节点内调用本地 LLM，不做「选哪个 skill」的推理。

## 结构

```
dag/
├── __main__.py      # 入口：python -m dag [--dataset ...] [--limit N]
├── pipeline.py      # PipelineConfig / StepDef / PipelineRunner（DAG 编排）
├── llm_client.py    # 本地 LLM 调用（OpenAI 兼容 /v1/chat/completions）
├── data/
│   ├── paper_dev.py # paper_dev.jsonl 加载器
│   └── paper_dev.jsonl
├── skills/
│   └── llm_skills.py  # query_gen / retrieve / evidence_extract / verify / output
└── README.md
```

- **编排**：`config/pipelines/fact_check.yaml` 定义步骤顺序（DAG）。
- **数据**：本框架数据在 `src/dag/data/`，与 FSM、ReAct 各自独立。

## 运行前

1. 启动本地 LLM（例如 Qwen3-VL）：
   ```bash
   bash script/run_qwen3vl_server.sh
   ```
   默认端口 1025；若不同可设 `LLM_BASE_URL=http://localhost:端口/v1`。

2. 在项目根目录执行（需把 `src` 加入 Python 路径）：

## 运行

```bash
# 单条示例
PYTHONPATH=src python -m dag

# 在 paper_dev 上评测（使用本框架 data/paper_dev.jsonl）
PYTHONPATH=src python -m dag --limit 100

# 指定数据集路径
PYTHONPATH=src python -m dag --dataset /path/to/file.jsonl --limit 20
```

输出会打印当前 DAG 步骤顺序（如 `query_gen → retrieve → evidence_extract → verify → output`）以及准确率、Per-class、预测分布。

## Skills

| skill_id        | 说明                     | LLM |
|-----------------|--------------------------|-----|
| query_gen       | 从 claim 生成检索 query  | ✓   |
| retrieve        | 检索（当前为占位，可接真实检索） | ✗   |
| evidence_extract| 从 snippets 抽一句或 NONE | ✓   |
| verify          | Support / Refute / NEI   | ✓   |
| output          | 格式化输出               | ✗   |

每条样本默认 3 次 LLM 调用：query_gen、evidence_extract、verify。

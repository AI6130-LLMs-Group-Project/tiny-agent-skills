# DAG (Pipeline) Framework

Fact-checking pipeline driven by a **directed acyclic graph**: step order is defined in config; each node is one skill; the small model is only called inside nodes (no LLM choosing "which skill next").

## Layout

Same structure as `fsm-based-method` and `react-based-method`: no `data/` inside the module; datasets live under project root `data/`.

```
dag/
├── __main__.py       # Entry + inline loaders for data/paper_dev.jsonl, data/ps/gsm8k/gsm8k.json
├── pipeline.py       # PipelineConfig, StepDef, PipelineRunner (DAG orchestration)
├── llm_client.py     # Local LLM client (OpenAI-compatible /v1/chat/completions)
├── skills/
│   └── llm_skills.py # query_gen, retrieve, evidence_extract, verify, output (+ math skills)
└── README.md
```

- **Orchestration**: `config/pipelines/fact_check.yaml` and `math_gsm8k.yaml` define the DAG (step order and optional `goto_if`).
- **Data**: Project root `data/` (e.g. `data/paper_dev.jsonl`, `data/ps/gsm8k/gsm8k.json`); loaders are inline in `__main__.py`.

## Before running

1. Start the local LLM (e.g. Qwen3-VL):
   ```bash
   bash script/run_qwen3vl_server.sh
   ```
   Default port is 1025. To use another port, set `LLM_BASE_URL=http://localhost:PORT/v1`.

2. Run from the project root with `src` on `PYTHONPATH`.

## Commands

```bash
# Single example
PYTHONPATH=src python3 -m dag

# Eval on paper_dev (uses data/paper_dev.jsonl)
PYTHONPATH=src python3 -m dag --limit 100

# Custom dataset
PYTHONPATH=src python3 -m dag --dataset /path/to/file.jsonl --limit 20
```

Output includes the current DAG step order (e.g. `query_gen → retrieve → evidence_extract → verify → output`) and, for eval, accuracy, per-class (gold), and prediction distribution.

## Skills (input → output)

| skill_id         | Input (from context)     | Output (merged into context)                    | LLM |
|------------------|---------------------------|--------------------------------------------------|-----|
| query_gen        | `claim`                   | `queries`, `last_step`                           | ✓   |
| retrieve         | `queries`                 | `snippets`, `last_step` (placeholder)            | ✗   |
| evidence_extract | `claim`, `snippets`       | `evidence`, `evidence_count`, `last_step`        | ✓   |
| verify           | `claim`, `evidence`       | `label` (Support\|Refute\|NEI), `last_step`      | ✓   |
| output           | `claim`, `label`          | `output`, `last_step`                            | ✗   |

Per sample there are **3 LLM calls**: query_gen, evidence_extract, verify.

"""
DAG pipeline CLI. Start local LLM first: bash script/run_qwen3vl_server.sh.

Usage:
  python -m dag                                    # single example (fact_check)
  python -m dag --pipeline math_gsm8k              # single math example
  python -m dag --limit N                          # eval fact_check on data/paper_dev.jsonl
  python -m dag --pipeline math_gsm8k --limit N    # eval math on data/ps/gsm8k/gsm8k.json
  python -m dag --dataset path.jsonl [--limit N]
  python -m dag --pipeline math_gsm8k --dataset data/ps/gsm8k/gsm8k.json [--limit N]

Data: like fsm-based-method and react-based-method, datasets live under project root data/
(e.g. data/paper_dev.jsonl, data/ps/gsm8k/gsm8k.json). No dag/data package.
"""

import json
import sys
from pathlib import Path
from typing import Iterator

import yaml

from dag.pipeline import PipelineConfig, PipelineRunner, load_pipeline_config_from_yaml
from dag.skills import fact_check_skill_registry, math_skill_registry

# -----------------------------------------------------------------------------
# Inline data loaders (project root data/, same layout as fsm/react)
# -----------------------------------------------------------------------------

_LABEL_MAP = {"SUPPORTS": "Support", "REFUTES": "Refute", "NOT ENOUGH INFO": "NEI"}


def _normalize_label(label: str) -> str:
    return _LABEL_MAP.get((label or "").upper().strip(), "NEI")


def _load_paper_dev(path: Path, limit: int | None = None) -> Iterator[dict]:
    """Read paper_dev.jsonl; yield dicts with claim, gold_label normalized."""
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                return
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row["_gold_label"] = _normalize_label(row.get("label", ""))
            yield row


def _load_gsm8k(path: Path, limit: int | None = None) -> Iterator[dict]:
    """Read gsm8k.json array; yield dicts with question, gold_answer."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        data = [data]
    for i, item in enumerate(data):
        if limit is not None and i >= limit:
            return
        yield {
            "question": item.get("question", ""),
            "gold_answer": float(item.get("answer", 0) or 0),
            "index": i,
        }

PIPELINE_FACT_CHECK = "fact_check"
PIPELINE_MATH_GSM8K = "math_gsm8k"
DEFAULT_PIPELINE = PIPELINE_FACT_CHECK


def _parse_args() -> tuple[Path, Path | None, int | None, str]:
    root = Path(__file__).resolve().parent.parent.parent
    limit = None
    dataset_path = None
    pipeline = DEFAULT_PIPELINE
    args = sys.argv[1:]
    if "--pipeline" in args:
        i = args.index("--pipeline")
        if i + 1 < len(args):
            pipeline = args[i + 1]
    if "--dataset" in args:
        i = args.index("--dataset")
        dataset_path = Path(args[i + 1]) if i + 1 < len(args) else None
    if "--limit" in args:
        i = args.index("--limit")
        if i + 1 < len(args):
            limit = int(args[i + 1])
    if dataset_path is None:
        dataset_path = (
            root / "data" / "ps" / "gsm8k" / "gsm8k.json"
            if pipeline == PIPELINE_MATH_GSM8K
            else root / "data" / "paper_dev.jsonl"
        )
    return root, dataset_path, limit, pipeline


def main() -> None:
    """CLI entry: parse --pipeline, --dataset, --limit; run single example or dataset eval."""
    root, dataset_path, limit, pipeline = _parse_args()
    run_dataset = ("--dataset" in sys.argv or "--limit" in sys.argv) and dataset_path and dataset_path.exists()

    if run_dataset:
        if pipeline == PIPELINE_MATH_GSM8K:
            run_math_gsm8k_dataset(root, dataset_path, limit=limit)
        else:
            run_pipeline_on_dataset(dataset_path, limit=limit, root=root)
    else:
        if pipeline == PIPELINE_MATH_GSM8K:
            run_math_gsm8k_example(root)
        else:
            run_fact_check_example(root)


def run_fact_check_example(root: Path) -> None:
    """
    Load fact_check.yaml, run pipeline once with a fixed claim.

    Input:  root — project root (for config path).
    Output: prints "Pipeline (DAG): ..." and "Pipeline result: ..." to stdout.
    """
    config_path = root / "config" / "pipelines" / "fact_check.yaml"
    if not config_path.exists():
        print("Skip: config/pipelines/fact_check.yaml not found")
        return
    with config_path.open() as f:
        data = yaml.safe_load(f)
    config = load_pipeline_config_from_yaml(data)
    print("Pipeline (DAG):", config.dag_str)
    runner = PipelineRunner(config=config, registry=fact_check_skill_registry())
    result = runner.run({"claim": "Newton was born in 1643."})
    print("Pipeline result:", result.get("output", result))


def run_math_gsm8k_example(root: Path) -> None:
    """Run math pipeline once with a fixed question."""
    config_path = root / "config" / "pipelines" / "math_gsm8k.yaml"
    if not config_path.exists():
        print("Skip: config/pipelines/math_gsm8k.yaml not found")
        return
    with config_path.open() as f:
        data = yaml.safe_load(f)
    config = load_pipeline_config_from_yaml(data)
    print("Pipeline (DAG):", config.dag_str)
    runner = PipelineRunner(config=config, registry=math_skill_registry())
    result = runner.run({"question": "Janet's ducks lay 16 eggs per day. She eats three for breakfast and bakes muffins with four. She sells the rest at $2 per egg. How much does she make daily?"})
    print("Pipeline result:", result.get("output", result))


def run_math_gsm8k_dataset(
    root: Path, dataset_path: Path, limit: int | None = None
) -> None:
    """Run math pipeline on GSM8K JSON; report accuracy (numeric match)."""
    config_path = root / "config" / "pipelines" / "math_gsm8k.yaml"
    if not config_path.exists():
        from dag.pipeline import PipelineConfig, StepDef
        config = PipelineConfig(steps=[
            StepDef("reason"),
            StepDef("extract_answer"),
            StepDef("output"),
        ])
    else:
        with config_path.open() as f:
            config = load_pipeline_config_from_yaml(yaml.safe_load(f))
    print("Pipeline (DAG):", config.dag_str)
    runner = PipelineRunner(config=config, registry=math_skill_registry())

    correct = 0
    total = 0
    for rec in _load_gsm8k(dataset_path, limit=limit):
        result = runner.run({"question": rec["question"]})
        pred = result.get("answer")
        if pred is None:
            pred = 0.0
        gold = rec["gold_answer"]
        total += 1
        if abs(float(pred) - float(gold)) < 1e-5:
            correct += 1
        if limit and total <= 5:
            print(f"  idx={rec['index']} pred={pred} gold={gold} ok={abs(float(pred) - float(gold)) < 1e-5}")

    if total:
        print(f"Accuracy: {correct}/{total} = {100.0 * correct / total:.1f}%")


def run_pipeline_on_dataset(
    dataset_path: Path, limit: int | None = None, root: Path | None = None
) -> None:
    """
    Run pipeline on each record in paper_dev.jsonl; print accuracy and per-class stats.

    Input:
      dataset_path — path to .jsonl file.
      limit        — optional max samples.
      root         — project root for config (default: inferred from __file__).

    Output: prints Accuracy, Per-class (gold), Prediction distribution to stdout.
    """
    root = root or Path(__file__).resolve().parent.parent.parent
    config_path = root / "config" / "pipelines" / "fact_check.yaml"
    if not config_path.exists():
        from dag.pipeline import PipelineConfig, StepDef
        config = PipelineConfig(steps=[
            StepDef("query_gen"),
            StepDef("retrieve"),
            StepDef("evidence_extract"),
            StepDef("verify", goto_if=("evidence_count < 1", 1)),
            StepDef("output"),
        ])
    else:
        with config_path.open() as f:
            config = load_pipeline_config_from_yaml(yaml.safe_load(f))
    print("Pipeline (DAG):", config.dag_str)
    runner = PipelineRunner(config=config, registry=fact_check_skill_registry())

    correct = 0
    total = 0
    gold_counts: dict[str, int] = {}
    gold_correct: dict[str, int] = {}
    pred_counts: dict[str, int] = {}

    for rec in _load_paper_dev(dataset_path, limit=limit):
        result = runner.run({"claim": rec["claim"]})
        pred = (result.get("label") or "NEI").strip()
        gold = rec["_gold_label"]
        total += 1
        gold_counts[gold] = gold_counts.get(gold, 0) + 1
        pred_counts[pred] = pred_counts.get(pred, 0) + 1
        if pred == gold:
            correct += 1
            gold_correct[gold] = gold_correct.get(gold, 0) + 1
        if limit and total <= 5:
            print(f"  id={rec.get('id')} claim={rec['claim'][:50]}... gold={gold} pred={pred}")

    if total:
        print(f"Accuracy: {correct}/{total} = {100.0 * correct / total:.1f}%")
        print("Per-class (gold):", {k: f"{gold_correct.get(k, 0)}/{gold_counts.get(k, 0)}" for k in ["Support", "Refute", "NEI"]})
        print("Prediction distribution:", pred_counts)


if __name__ == "__main__":
    main()

"""
DAG pipeline CLI. Start local LLM first: bash script/run_qwen3vl_server.sh.

Usage:
  python -m dag                    # single example run
  python -m dag --limit N         # eval on dag/data/paper_dev.jsonl, max N samples
  python -m dag --dataset path.jsonl [--limit N]
"""

import sys
from pathlib import Path

import yaml

from dag.pipeline import PipelineConfig, PipelineRunner, load_pipeline_config_from_yaml
from dag.skills import fact_check_skill_registry


def main() -> None:
    """CLI entry: parse --dataset, --limit; run single example or dataset eval."""
    root = Path(__file__).resolve().parent.parent.parent
    default_dataset = Path(__file__).resolve().parent / "data" / "paper_dev.jsonl"
    dataset_path = default_dataset
    limit = None
    args = sys.argv[1:]
    if "--dataset" in args:
        i = args.index("--dataset")
        dataset_path = Path(args[i + 1]) if i + 1 < len(args) else default_dataset
    if "--limit" in args:
        i = args.index("--limit")
        if i + 1 < len(args):
            limit = int(args[i + 1])

    if ("--dataset" in sys.argv or "--limit" in sys.argv) and dataset_path.exists():
        run_pipeline_on_dataset(dataset_path, limit=limit, root=root)
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
    from dag.data import load_paper_dev

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

    for rec in load_paper_dev(dataset_path, limit=limit):
        result = runner.run({"claim": rec.claim})
        pred = (result.get("label") or "NEI").strip()
        gold = rec.gold_label
        total += 1
        gold_counts[gold] = gold_counts.get(gold, 0) + 1
        pred_counts[pred] = pred_counts.get(pred, 0) + 1
        if pred == gold:
            correct += 1
            gold_correct[gold] = gold_correct.get(gold, 0) + 1
        if limit and total <= 5:
            print(f"  id={rec.id} claim={rec.claim[:50]}... gold={gold} pred={pred}")

    if total:
        print(f"Accuracy: {correct}/{total} = {100.0 * correct / total:.1f}%")
        print("Per-class (gold):", {k: f"{gold_correct.get(k, 0)}/{gold_counts.get(k, 0)}" for k in ["Support", "Refute", "NEI"]})
        print("Prediction distribution:", pred_counts)


if __name__ == "__main__":
    main()

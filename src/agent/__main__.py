import sys
from pathlib import Path

import yaml

from agent.pipeline import PipelineConfig, PipelineRunner, load_pipeline_config_from_yaml
from agent.skills import fact_check_skill_registry


def main() -> None:
    """Entry point for the agent CLI. 需先启动本地 LLM：bash script/run_qwen3vl_server.sh"""
    root = Path(__file__).resolve().parent.parent.parent
    dataset_path = root / "paper_dev.jsonl"
    limit = None
    args = sys.argv[1:]
    if "--dataset" in args:
        i = args.index("--dataset")
        dataset_path = Path(args[i + 1]) if i + 1 < len(args) else dataset_path
    if "--limit" in args:
        i = args.index("--limit")
        if i + 1 < len(args):
            limit = int(args[i + 1])

    if "--dataset" in sys.argv and dataset_path.exists():
        run_pipeline_on_dataset(dataset_path, limit=limit)
    else:
        run_fact_check_example(root)


def run_fact_check_example(root: Path) -> None:
    """加载 fact_check.yaml，跑一遍 Pipeline（本地 LLM）。"""
    config_path = root / "config" / "pipelines" / "fact_check.yaml"
    if not config_path.exists():
        print("Skip: config/pipelines/fact_check.yaml not found")
        return
    with config_path.open() as f:
        data = yaml.safe_load(f)
    config = load_pipeline_config_from_yaml(data)
    runner = PipelineRunner(config=config, registry=fact_check_skill_registry())
    result = runner.run({"claim": "Newton was born in 1643."})
    print("Pipeline result:", result.get("output", result))


def run_pipeline_on_dataset(dataset_path: Path, limit: int | None = None) -> None:
    """对 paper_dev.jsonl 逐条跑 Pipeline，打印准确率。"""
    from agent.data import load_paper_dev

    config_path = dataset_path.parent / "config" / "pipelines" / "fact_check.yaml"
    if not config_path.exists():
        from agent.pipeline import PipelineConfig, StepDef
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

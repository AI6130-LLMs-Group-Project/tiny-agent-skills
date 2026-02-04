"""数据加载：paper_dev.jsonl 等事实核查数据集。"""

from .paper_dev import load_paper_dev, PaperDevRecord, normalize_label

__all__ = ["load_paper_dev", "PaperDevRecord", "normalize_label"]

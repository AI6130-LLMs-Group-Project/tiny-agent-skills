"""
paper_dev.jsonl 加载器。

每行一条事实核查样本：
- id, verifiable, label (SUPPORTS | REFUTES | NOT ENOUGH INFO), claim, evidence
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

# 与 pipeline 输出统一：Support / Refute / NEI
LABEL_MAP = {
    "SUPPORTS": "Support",
    "REFUTES": "Refute",
    "NOT ENOUGH INFO": "NEI",
}


def normalize_label(label: str) -> str:
    """把数据集的 label 转为与 pipeline 一致的 Support / Refute / NEI。"""
    return LABEL_MAP.get(label.upper().strip(), "NEI")


def load_paper_dev(path: str | Path, limit: int | None = None) -> Iterator[PaperDevRecord]:
    """逐条读取 paper_dev.jsonl，返回 PaperDevRecord。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                return
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            yield PaperDevRecord(
                id=data.get("id"),
                claim=data.get("claim", ""),
                label=data.get("label", ""),
                verifiable=data.get("verifiable", ""),
                evidence=data.get("evidence", []),
            )


class PaperDevRecord:
    """单条 paper_dev 样本。"""

    __slots__ = ("id", "claim", "label", "verifiable", "evidence")

    def __init__(
        self,
        id: int | str | None = None,
        claim: str = "",
        label: str = "",
        verifiable: str = "",
        evidence: list | None = None,
    ):
        self.id = id
        self.claim = claim
        self.label = label
        self.verifiable = verifiable
        self.evidence = evidence or []

    @property
    def gold_label(self) -> str:
        """与 pipeline 输出可比的标签：Support / Refute / NEI。"""
        return normalize_label(self.label)

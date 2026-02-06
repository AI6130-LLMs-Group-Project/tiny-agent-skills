"""
Loader for paper_dev.jsonl: one fact-verification sample per line.

Schema per line: id, verifiable, label (SUPPORTS | REFUTES | NOT ENOUGH INFO), claim, evidence.
Labels are normalized to pipeline output: Support, Refute, NEI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

LABEL_MAP = {
    "SUPPORTS": "Support",
    "REFUTES": "Refute",
    "NOT ENOUGH INFO": "NEI",
}


def normalize_label(label: str) -> str:
    """
    Input:  label — raw dataset label (e.g. "SUPPORTS", "REFUTES", "NOT ENOUGH INFO").
    Output: "Support" | "Refute" | "NEI" for pipeline comparison.
    """
    return LABEL_MAP.get(label.upper().strip(), "NEI")


def load_paper_dev(path: str | Path, limit: int | None = None) -> Iterator[PaperDevRecord]:
    """
    Read paper_dev.jsonl line by line.

    Input:
      path  — path to .jsonl file.
      limit — optional max number of records to yield.

    Output:
      Iterator[PaperDevRecord] — one record per line.
    """
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
    """
    One paper_dev sample.

    Input (from JSONL): id, claim, label, verifiable, evidence.
    Output (for pipeline): .claim (str), .gold_label ("Support"|"Refute"|"NEI").
    """

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
        """Normalized label for pipeline comparison: Support | Refute | NEI."""
        return normalize_label(self.label)

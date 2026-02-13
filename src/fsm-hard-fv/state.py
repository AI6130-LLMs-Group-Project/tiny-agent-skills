from __future__ import annotations

import os
from pathlib import Path
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


### Load environment variables from a .env file
def load_env():
    if getattr(load_env, "_loaded", False):
        return
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"
    if env_path.is_file():
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k and k not in os.environ:
                    os.environ[k] = v
    load_env._loaded = True


### Data Classes =======================

@dataclass
class EvidenceItem:
    eid: str
    claim_id: str
    s: str
    src: str
    d: Optional[str] = None
    cred: str = "med" # not meh!


@dataclass
class ActionRecord:
    ts: str
    state: str
    name: str
    status: str
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:
    sid: str
    fsm: str
    rev: int = 0
    claim: Optional[str] = None
    norm_claim: Optional[str] = None
    claims: List[Dict[str, Any]] = field(default_factory=list)
    plans: List[Dict[str, Any]] = field(default_factory=list)
    tool_requests: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[EvidenceItem] = field(default_factory=list)
    selected: List[Dict[str, Any]] = field(default_factory=list)
    scores: List[Dict[str, Any]] = field(default_factory=list)
    verdicts: List[Dict[str, Any]] = field(default_factory=list)
    output: Optional[Dict[str, Any]] = None
    history: List[ActionRecord] = field(default_factory=list)

    def tick(self, next_state: str):
        self.rev += 1
        self.fsm = next_state

    def add_history(self, name: str, status: str, detail: Optional[Dict[str, Any]] = None):
        self.history.append(
            ActionRecord(
                ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
                state=self.fsm,
                name=name,
                status=status,
                detail=detail or {},
            )
        )

    def add_evidence(self, items: List[EvidenceItem]):
        self.evidence.extend(items)

    def to_dict(self):
        return {
            "sid": self.sid,
            "fsm": self.fsm,
            "rev": self.rev,
            "claim": self.claim,
            "norm_claim": self.norm_claim,
            "claims": self.claims,
            "plans": self.plans,
            "tool_requests": self.tool_requests,
            "evidence": [e.__dict__ for e in self.evidence],
            "selected": self.selected,
            "scores": self.scores,
            "verdicts": self.verdicts,
            "output": self.output,
            "history": [h.__dict__ for h in self.history],
        }

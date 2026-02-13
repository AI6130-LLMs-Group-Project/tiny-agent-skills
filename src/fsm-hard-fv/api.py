### API module for FSM-based fact verification service
### Please host it using uvicorn (of course free choice, but recommended)

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from orchestrator import Orchestrator
from state import AgentState


class VerifyRequest(BaseModel):
    claim: str = Field(..., min_length=3)
    explain: bool = False
    trace: bool = False


class VerifyResponse(BaseModel):
    decision: str
    explanation: Optional[str] = None
    trace: Optional[List[Dict[str, Any]]] = None


app = FastAPI(title="FSM Fact Verification")


def _map_verdicts(verdicts: List[Dict[str, Any]]) -> str:
    labels = [v.get("v") for v in verdicts]
    if any(v == "refuted" for v in labels):
        return "REFUTE"
    if any(v == "supported" for v in labels):
        return "SUPPORT"
    return "NO ENOUGH INFO"


def _build_explanation(state: AgentState, decision: str) -> str:
    selected_ids = {s.get("eid") for s in state.selected}
    quotes = []
    for ev in state.evidence:
        if ev.eid in selected_ids and ev.s:
            quotes.append(f"\"{ev.s}\"")
    if quotes:
        joined = " ".join(quotes[:5])
        return f"{decision}. Evidence: {joined}"
    return f"{decision}. Evidence is insufficient."


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest) -> VerifyResponse:
    sid = f"s{int(time.time())}"
    state = AgentState(sid=sid, fsm="PARSE_CLAIM")
    orch = Orchestrator(state)
    try:
        result = orch.run(req.claim)
    except Exception:
        decision = "NO ENOUGH INFO"
        explanation = f"{decision}. Pipeline exception fallback." if req.explain else None
        trace = [h.__dict__ for h in state.history] if req.trace else None
        return VerifyResponse(decision=decision, explanation=explanation, trace=trace)
    if result.get("s") != "ok":
        decision = "NO ENOUGH INFO"
        explanation = None
        if req.explain:
            err = result.get("e") or {}
            explanation = f"{decision}. Pipeline fallback due to internal validation failure ({err.get('code', 'UNKNOWN')})."
        trace = [h.__dict__ for h in state.history] if req.trace else None
        return VerifyResponse(decision=decision, explanation=explanation, trace=trace)
    decision = _map_verdicts(state.verdicts)
    explanation = _build_explanation(state, decision) if req.explain else None
    trace = [h.__dict__ for h in state.history] if req.trace else None
    return VerifyResponse(decision=decision, explanation=explanation, trace=trace)

# TO Be Continued (BGM: roundabout) >>>

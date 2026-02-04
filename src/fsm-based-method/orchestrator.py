### Orchestrator for FSM-based Fact-Checking Agent (refers to the Architecture diagram)

from __future__ import annotations

import json
import os
import re
import urllib.request
import importlib.util
from typing import Any, Dict, List, Set

from guardrail import basic_check, check_tool_output, extract_evidence_rows, sanitize
from policy import allow_skill, allow_tool
from skills import registry as skill_registry
from state import AgentState, EvidenceItem, load_env


### LLM Client and Tool Executor =====================

class LlamaCppClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")

    def complete(self, system: str, user: str, temperature: float = 0.0, max_tokens: int = 512) -> str:
        url = self.endpoint + "/completion"
        prompt = f"{system}\n\n{user}\n"
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "n_predict": max_tokens,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("content", "")


class ToolExecutor:
    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def _load_module(self, tool_id: str):
        if tool_id in self._cache:
            return self._cache[tool_id]
        meta = skill_registry.TOOLS.get(tool_id)
        if not meta:
            raise ValueError("unknown tool: " + tool_id)
        path = meta["path"]
        spec = importlib.util.spec_from_file_location(tool_id, path)
        mod = importlib.util.module_from_spec(spec)
        if spec and spec.loader:
            spec.loader.exec_module(mod)
        self._cache[tool_id] = mod
        return mod

    def run(self, tool_id: str, args: Dict[str, Any]):
        mod = self._load_module(tool_id)
        if not hasattr(mod, "run"):
            raise ValueError("tool has no run(): " + tool_id)
        return mod.run(args)


def _load_skill_text(skill_id: str) -> str:
    meta = skill_registry.SKILLS.get(skill_id)
    if not meta:
        raise ValueError("unknown skill: " + skill_id)
    with open(meta["path"], "r", encoding="utf-8") as f:
        return f.read()


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    decoder = json.JSONDecoder()

    # Try direct decode first (fast path).
    try:
        obj, _ = decoder.raw_decode(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Fallback: scan for the first JSON object
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj

    raise ValueError("no valid JSON object found")


### Main Orchestrator Class ===================

### A reminder from Hanny:
# s -> status
# d -> data
# e -> error
# rb -> rollback
### Shorten the entry name can save tokens in multi-round LLM calls. So I did it.

class Orchestrator:
    def __init__(self, state: AgentState):
        load_env()
        endpoint = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:1025") # Not localhost~
        self.n_retry = int(os.getenv("N_RETRY", "2"))
        if self.n_retry < 0:
            self.n_retry = 0
        self.llm = LlamaCppClient(endpoint)
        self.state = state
        self.tools = ToolExecutor()

    def _call_skill(self, skill_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not allow_skill(self.state.fsm, skill_id):
            return {"s": "error", "d": None, "e": {"code": "SCOPE", "msg": "skill not allowed"}, "rb": "state"}
        skill_text = _load_skill_text(skill_id)
        system = (
            "You MUST output STRICT JSON only.\n"
            "Return exactly one JSON object with top-level keys: s, d, e, rb.\n"
            "Allowed s: ok|error|retry. No markdown. No prose."
        )
        user = skill_text + "\n\nINPUT:\n" + json.dumps(input_data, ensure_ascii=True)
        last_err = "unknown"
        for attempt in range(self.n_retry + 1):
            prompt_suffix = ""
            if attempt > 0:
                prompt_suffix = "\n\nIMPORTANT: prior output failed schema/JSON checks. Output one JSON object only."
            raw = self.llm.complete(system, user + prompt_suffix, temperature=0.0, max_tokens=512)
            try:
                data = _extract_json(raw)
            except Exception as exc:
                last_err = f"BAD_JSON: {exc}"
                continue
            data = sanitize(data)
            ok, msg = basic_check(data)
            if not ok:
                last_err = "BAD_SCHEMA: " + msg
                continue
            return data
        return {"s": "error", "d": None, "e": {"code": "BAD_OUTPUT", "msg": last_err}, "rb": "state"}

    def _is_web_search_enabled(self) -> bool:
        provider = os.getenv("WEB_SEARCH_PROVIDER", "").strip().lower()
        if provider == "serpapi":
            return bool(os.getenv("SERPAPI_KEY"))
        # If you have question on this, it's because we wanna utilise free credits XD
        if provider == "tavily":
            return bool(os.getenv("TAVILY_API_KEY"))
        # If provider is unset, allow explicit keys.
        return bool(os.getenv("SERPAPI_KEY") or os.getenv("TAVILY_API_KEY"))

    def _run_tool_with_retry(self, tool_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        out = None
        last_err = ""
        for _ in range(self.n_retry + 1):
            try:
                out = self.tools.run(tool_id, args)
            except Exception as exc:
                out = None
                last_err = str(exc)
            ok, msg = check_tool_output(out)
            if ok:
                return out
            last_err = msg
        return {"s": "error", "d": None, "e": {"code": "BAD_TOOL_OUTPUT", "msg": last_err}}

    def _rows_to_evidence(self, rows: List[Dict[str, Any]], claim_id: str) -> List[EvidenceItem]:
        items: List[EvidenceItem] = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            text = r.get("snippet") or r.get("title") or ""
            if not text:
                continue
            eid = f"{r.get('src','web')}:{r.get('rid','')}"
            items.append(
                EvidenceItem(
                    eid=eid,
                    claim_id=claim_id,
                    s=text,
                    src=r.get("url") or r.get("src", ""),
                    d=r.get("d"),
                    cred=r.get("cred", "med"),
                )
            )
        return items

    def _exec_tool_requests(self, requests: List[Dict[str, Any]]) -> List[EvidenceItem]:
        collected: List[EvidenceItem] = []
        for tr in requests:
            args = tr.get("args", {})
            claim_id = tr.get("for", "")
            q = args.get("q", "")
            lim = args.get("lim", 3)

            # Priority: wiki search (free!) > local kb_lookup (free~) > web_search (API Key... $$$)
            candidates: List[Dict[str, Any]] = []
            if allow_tool(self.state.fsm, "search"):
                candidates.append({"tool": "search", "args": {"q": q, "lim": lim, "src": "wiki"}})
            if allow_tool(self.state.fsm, "kb_lookup"):
                candidates.append({"tool": "kb_lookup", "args": {"q": q, "lim": lim}})
            if allow_tool(self.state.fsm, "web_search") and self._is_web_search_enabled():
                candidates.append({"tool": "web_search", "args": {"q": q, "lim": lim}})

            got_rows = False
            for cand in candidates:
                tool_id = cand["tool"]
                tool_args = cand["args"]
                out = self._run_tool_with_retry(tool_id, tool_args)
                self.state.add_history(f"tool:{tool_id}", out.get("s", "error"), {"args": tool_args, "e": out.get("e")})
                if out.get("s") != "ok":
                    continue
                rows = extract_evidence_rows(out)
                if not rows:
                    continue
                collected.extend(self._rows_to_evidence(rows, claim_id))
                got_rows = True
                break

            if not got_rows:
                self.state.add_history("tool:retrieval_miss", "retry", {"q": q, "claim_id": claim_id})
        return collected

    def _fallback_select_evidence(self, ev_in: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        claim_text = " ".join(c.get("c", "") for c in self.state.claims).lower()
        claim_terms: Set[str] = set(re.findall(r"[a-z0-9]+", claim_text))
        scored: List[Dict[str, Any]] = []
        for ev in ev_in:
            sent = (ev.get("s") or "").lower()
            sent_terms = set(re.findall(r"[a-z0-9]+", sent))
            overlap = len(claim_terms.intersection(sent_terms))
            if overlap > 0:
                scored.append({"eid": ev.get("eid"), "for": ev.get("for"), "score": overlap})
        scored.sort(key=lambda x: (-x["score"], str(x.get("eid", ""))))
        return [{"eid": s.get("eid"), "for": s.get("for")} for s in scored[:5] if s.get("eid")]

    def _set_default_verdicts(self):
        verdicts = []
        for c in self.state.claims:
            verdicts.append({"id": c.get("id", "s1"), "v": "insufficient", "conf": "low"})
        self.state.verdicts = verdicts

    def run(self, claim: str) -> Dict[str, Any]:
        self.state.claim = claim
        state_retries: Dict[str, int] = {}
        max_steps = 20
        steps = 0
        while steps < max_steps:
            steps += 1
            
            # State Machine Behaviors
            if self.state.fsm == "PARSE_CLAIM":
                out = self._run_tool_with_retry(
                    "claim_normalize",
                    {"c": claim, "ctx": None, "lang": "en", "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}},
                )
                if out.get("s") != "ok":
                    out = self._call_skill("claim_normalizer", {"c": claim, "ctx": None, "lang": "en", "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}})
                self.state.add_history("claim_normalizer", out["s"], out)
                if out["s"] != "ok":
                    self._set_default_verdicts()
                    self.state.tick("OUTPUT")
                    continue
                d = out.get("d") or {}
                self.state.norm_claim = d.get("nc")
                if d.get("sd"):
                    out2 = self._run_tool_with_retry(
                        "claim_decompose",
                        {"nc": d.get("nc"), "lang": "en", "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}},
                    )
                    if out2.get("s") != "ok":
                        out2 = self._call_skill("claim_decomposer", {"nc": d.get("nc"), "lang": "en", "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}})
                    self.state.add_history("claim_decomposer", out2["s"], out2)
                    if out2["s"] == "ok":
                        self.state.claims = out2.get("d", {}).get("subs", [])
                else:
                    self.state.claims = [{"id": "s1", "c": d.get("nc", claim)}]
                out3 = self._call_skill("evidence_query_planner", {"claims": self.state.claims, "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}, "hints": None})
                self.state.add_history("evidence_query_planner", out3["s"], out3)
                self.state.plans = out3.get("d", {}).get("plans", []) if out3["s"] == "ok" else []
                self.state.tick("RETRIEVAL")
                continue

            if self.state.fsm == "RETRIEVAL":
                out = self._run_tool_with_retry(
                    "tool_request_compose",
                    {"plans": self.state.plans, "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}},
                )
                if out.get("s") != "ok":
                    out = self._call_skill("tool_request_composer", {"plans": self.state.plans, "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}})
                self.state.add_history("tool_request_composer", out["s"], out)
                if out["s"] != "ok":
                    tries = state_retries.get("RETRIEVAL", 0) + 1
                    state_retries["RETRIEVAL"] = tries
                    if tries <= self.n_retry:
                        self.state.tick("RETRIEVAL")
                        continue
                    self._set_default_verdicts()
                    self.state.tick("OUTPUT")
                    continue

                self.state.tool_requests = out.get("d", {}).get("tr", [])
                ev = self._exec_tool_requests(self.state.tool_requests)
                if ev:
                    self.state.add_evidence(ev)
                    self.state.tick("SELECT_EVIDENCE")
                    continue

                # Empty evidence is still valid: retry retrieval TOP_N times before conclude a NEI
                tries = state_retries.get("RETRIEVAL_EMPTY", 0) + 1
                state_retries["RETRIEVAL_EMPTY"] = tries
                self.state.add_history("retrieval_empty", "retry", {"tries": tries})
                if tries <= self.n_retry:
                    self.state.tick("RETRIEVAL")
                    continue
                self._set_default_verdicts()
                self.state.tick("OUTPUT")
                continue

            if self.state.fsm == "SELECT_EVIDENCE":
                ev_in = [
                    {"eid": e.eid, "for": e.claim_id, "s": e.s, "src": e.src, "d": e.d, "cred": e.cred}
                    for e in self.state.evidence
                ]
                if not ev_in:
                    self.state.tick("RETRIEVAL")
                    continue
                out = self._call_skill("evidence_filter", {"claims": self.state.claims, "ev": ev_in, "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}})
                self.state.add_history("evidence_filter", out["s"], out)
                if out["s"] == "ok":
                    self.state.selected = out.get("d", {}).get("sel", [])
                if not self.state.selected:
                    fallback_sel = self._fallback_select_evidence(ev_in)
                    if fallback_sel:
                        self.state.selected = fallback_sel
                        self.state.add_history("evidence_filter_fallback", "ok", {"selected_n": len(fallback_sel)})
                if self.state.selected:
                    self.state.tick("NLI_VERIFY")
                    continue
                tries = state_retries.get("SELECT_EVIDENCE_EMPTY", 0) + 1
                state_retries["SELECT_EVIDENCE_EMPTY"] = tries
                if tries <= self.n_retry:
                    self.state.tick("RETRIEVAL")
                    continue
                self._set_default_verdicts()
                self.state.tick("OUTPUT")
                continue

            if self.state.fsm == "NLI_VERIFY":
                selected_ids = {s.get("eid") for s in self.state.selected}
                sel_in = [{"eid": e.eid, "for": e.claim_id, "s": e.s, "cred": e.cred} for e in self.state.evidence if e.eid in selected_ids]
                if not sel_in:
                    self._set_default_verdicts()
                    self.state.tick("OUTPUT")
                    continue
                out = self._call_skill("evidence_stance_scorer", {"claims": self.state.claims, "sel": sel_in, "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}})
                self.state.add_history("evidence_stance_scorer", out["s"], out)
                if out["s"] == "ok":
                    self.state.scores = out.get("d", {}).get("scores", [])
                    self.state.tick("DECIDE")
                    continue
                self._set_default_verdicts()
                self.state.tick("OUTPUT")
                continue

            if self.state.fsm == "DECIDE":
                out = self._call_skill("verdict_aggregator", {"claims": self.state.claims, "scores": self.state.scores, "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}})
                self.state.add_history("verdict_aggregator", out["s"], out)
                if out["s"] == "ok":
                    self.state.verdicts = out.get("d", {}).get("ver", [])
                if not self.state.verdicts:
                    self._set_default_verdicts()
                self.state.tick("OUTPUT")
                continue

            if self.state.fsm == "OUTPUT":
                if not self.state.verdicts:
                    self._set_default_verdicts()
                out = self._call_skill("response_composer", {"claims": self.state.claims, "ver": self.state.verdicts, "use": self.state.selected, "st": {"sid": self.state.sid, "rev": self.state.rev, "fsm": self.state.fsm}})
                self.state.add_history("response_composer", out["s"], out)
                if out["s"] == "ok":
                    self.state.output = out.get("d")
                    return out
                # Final fallback that still returns valid output
                return {
                    "s": "ok",
                    "d": {"out": [{"id": c.get("id", "s1"), "ver": "insufficient", "conf": "low", "r": "Insufficient evidence after retries.", "cite": []} for c in self.state.claims]},
                    "e": None,
                    "rb": "none",
                }

        self._set_default_verdicts()
        return {"s": "ok", "d": {"out": [{"id": c.get("id", "s1"), "ver": "insufficient", "conf": "low", "r": "Max steps reached.", "cite": []} for c in self.state.claims]}, "e": None, "rb": "none"}

# Algorithms are FUN !!

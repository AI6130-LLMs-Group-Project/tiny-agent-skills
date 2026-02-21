from __future__ import annotations

import importlib.util
import json
import os
import re
import socket
import urllib.request
from urllib.parse import urlparse
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from fsm import next_state as fsm_next_state
from guardrail import check_action_payload, check_tool_output, extract_evidence_rows, extract_json_object
from orchestrator_helpers import (
    clean_text,
    coerce_int,
    env_int,
    first_dict,
    first_list,
    load_text,
    normalize_conf,
    normalize_stance,
    normalize_verdict,
    safe_claims,
    to_query_list,
)
from skills import registry as skill_registry
from state import AgentState, EvidenceItem, load_env


_STAGE_MSG: Dict[str, Tuple[str, str]] = {
    "PARSE_CLAIM": (
        "The agent rewrote the claim into verification-friendly subclaims.",
        "Next it will generate retrieval queries for each subclaim.",
    ),
    "RETRIEVAL": (
        "The agent is collecting candidate evidence from retrieval tools.",
        "Next it will pick the most relevant evidence snippets.",
    ),
    "SELECT_EVIDENCE": (
        "The agent filtered evidence and kept high-signal snippets.",
        "Next it will judge support/refute/neutral stance.",
    ),
    "NLI_VERIFY": (
        "The agent scored claim-evidence stance pairs.",
        "Next it will aggregate scores into verdicts.",
    ),
    "DECIDE": (
        "The agent produced verdicts from stance evidence.",
        "Next it will compose final output with rationale and cites.",
    ),
    "OUTPUT": (
        "The agent produced final output for this claim.",
        "Next it will move to the next FEVER sample.",
    ),
    "PARSE_PROBLEM": (
        "The agent parsed the math question into target and givens.",
        "Next it will create a step-by-step solution plan.",
    ),
    "PLAN_SOLUTION": (
        "The agent drafted a compact arithmetic plan.",
        "Next it will execute calculations from the plan.",
    ),
    "EXECUTE_SOLUTION": (
        "The agent computed a candidate numeric answer.",
        "Next it will self-check the result for consistency.",
    ),
    "VERIFY_SOLUTION": (
        "The agent verified the computed answer against the question.",
        "Next it will format the final GSM output.",
    ),
}

class LlamaCppClient:
    def __init__(self, endpoint: str):
        self.endpoint = (endpoint or "").rstrip("/")

    def complete(self, system: str, user: str, temperature: float = 0.0, max_tokens: int = 512) -> str:
        if not self.endpoint:
            raise RuntimeError("LLM endpoint is empty")
        url = self.endpoint + "/completion"
        payload = {
            "prompt": f"{system}\n\n{user}\n",
            "temperature": temperature,
            "n_predict": max_tokens,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            timeout_s = float(os.getenv("LLM_HTTP_TIMEOUT", "8"))
        except Exception:
            timeout_s = 8.0
        timeout_s = min(60.0, max(6.0, timeout_s))
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
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
            raise ValueError(f"unknown tool: {tool_id}")
        spec = importlib.util.spec_from_file_location(tool_id, meta["path"])
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load tool module: {tool_id}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self._cache[tool_id] = mod
        return mod

    def run(self, tool_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        mod = self._load_module(tool_id)
        if not hasattr(mod, "run"):
            raise ValueError(f"tool has no run(): {tool_id}")
        return mod.run(args)


class Orchestrator:
    def __init__(self, state: AgentState):
        load_env()
        self.state = state
        self.llm = LlamaCppClient(os.getenv("LLM_ENDPOINT", "http://127.0.0.1:1025"))
        self.tools = ToolExecutor()
        self.n_retry = max(0, env_int(os.getenv,"N_RETRY", 2))
        self.llm_retry = max(0, env_int(os.getenv,"LLM_JSON_RETRY", 1))
        self.max_steps = max(6, env_int(os.getenv,"SOFT_FSM_MAX_STEPS", 20))
        self.max_math_tool_calls = max(1, env_int(os.getenv, "SOFT_FSM_MATH_MAX_TOOL_CALLS", 3))
        self.top_n = max(1, env_int(os.getenv, "TOP_N", 3))
        self.wiki_fetch_limit = max(0, env_int(os.getenv, "WIKI_FETCH_LIMIT", 3))
        self.subskill_hint_chars = max(500, env_int(os.getenv,"SUBSKILL_HINT_CHARS", 1000))
        self.controller_hint_chars = max(300, env_int(os.getenv,"CONTROLLER_HINT_CHARS", 700))
        self.controller_skills = {
            "fever": load_text(skill_registry.SKILLS["fsm_fact_verification"]["path"]),
            "gsm8k": load_text(skill_registry.SKILLS["fsm_math_solver"]["path"]),
        }
        self.subskills = {name: load_text(meta["path"]) for name, meta in skill_registry.SUBSKILLS.items()}
        self.llm_enabled = self._probe_llm()
        self.network_enabled = self._probe_host("en.wikipedia.org", 443)
        self.llm_fail_streak = 0
        self.llm_disable_after = max(0, env_int(os.getenv,"LLM_DISABLE_AFTER_FAILS", 12))

    def _probe_llm(self) -> bool:
        if os.getenv("SOFT_FSM_FORCE_FALLBACK", "0").strip().lower() in {"1", "true", "yes"}:
            return False
        parsed = urlparse(self.llm.endpoint)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return self._probe_host(host, port)

    def _probe_host(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.8):
                return True
        except Exception:
            return False

    def _run_tool_with_retry(self, tool_id: str, args: Dict[str, Any], retries: Optional[int] = None) -> Dict[str, Any]:
        last_err = "unknown"
        max_retry = self.n_retry if retries is None else max(0, retries)
        for _ in range(max_retry + 1):
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

    def _note_llm_failure(self) -> None:
        self.llm_fail_streak += 1
        if self.llm_disable_after > 0 and self.llm_fail_streak >= self.llm_disable_after:
            self.llm_enabled = False
            self.state.add_history("llm_disabled", "retry", {"fail_streak": self.llm_fail_streak})

    def _note_llm_success(self) -> None:
        self.llm_fail_streak = 0

    def _subskill_hint(self, subskill_id: str, max_chars: Optional[int] = None) -> str:
        text = (self.subskills.get(subskill_id, "") or "").strip()
        if not text:
            return ""
        lim = self.subskill_hint_chars if max_chars is None else max_chars
        return text[:lim]

    def _task_name(self) -> str:
        task = (self.state.task or "fever").strip().lower()
        if task in {"fact", "fact_verification", "fact-verification"}:
            return "fever"
        if task in {"gsm", "math", "gsm8k"}:
            return "gsm8k"
        return "fever"

    def _controller_hint(self, max_chars: Optional[int] = None) -> str:
        text = (self.controller_skills.get(self._task_name()) or self.controller_skills.get("fever") or "").strip()
        if not text:
            return ""
        lim = self.controller_hint_chars if max_chars is None else max_chars
        return text[:lim]

    def _llm_schema_mismatch(self, subskill: str, llm_out: Dict[str, Any]) -> None:
        self.state.add_history("llm_schema_mismatch", "retry", {"subskill": subskill, "keys": list(llm_out.keys())[:8]})

    def _call_llm_json(
        self,
        subskill_id: str,
        output_contract: str,
        payload: Dict[str, Any],
        max_tokens: int = 700,
        include_controller: bool = True,
    ) -> Optional[Dict[str, Any]]:
        if not self.llm_enabled:
            return None
        task_name = self._task_name()
        system = (
            f"You are an FSM {task_name} sub-agent under soft constraints. "
            "Follow policy and stage subskill, then output one JSON object only."
        )
        hint = self._subskill_hint(subskill_id)
        policy = self._controller_hint() if include_controller else ""
        policy_block = f"Controller policy:\n{policy}\n\n" if policy else ""
        user = (
            policy_block
            + f"Subskill id: {subskill_id}\n"
            + f"Hint:\n{hint}\n\n"
            + f"Output contract:\n{output_contract}\n\n"
            + f"Input:\n{json.dumps(payload, ensure_ascii=True)}\n\n"
            + "Return only one JSON object."
        )
        last_raw = ""
        last_err = "unknown"
        for attempt in range(self.llm_retry + 1):
            prompt = user
            req_tokens = max_tokens
            if attempt > 0:
                prompt = (
                    f"Subskill id: {subskill_id}\n"
                    f"Hint:\n{self._subskill_hint(subskill_id, max_chars=320)}\n\n"
                    f"Output contract:\n{output_contract}\n\n"
                    f"Input:\n{json.dumps(payload, ensure_ascii=True)}\n\n"
                    "Return one JSON object only."
                )
                req_tokens = min(max_tokens, 240)
            try:
                raw = self.llm.complete(system, prompt, temperature=0.0, max_tokens=req_tokens)
                last_raw = (raw or "")[:200]
                obj = extract_json_object(raw)
                if isinstance(obj, dict):
                    self._note_llm_success()
                    return obj
            except Exception as exc:
                last_err = str(exc)
                continue
        self.state.add_history("llm_json_fail", "retry", {"subskill": subskill_id, "err": last_err[:120], "raw": last_raw})
        self._note_llm_failure()
        return None

    def _advance(self, status: str) -> None:
        self.state.tick(fsm_next_state(self.state.fsm, status, self._task_name()))

    def _is_web_search_enabled(self) -> bool:
        if not self.network_enabled:
            return False
        provider = os.getenv("WEB_SEARCH_PROVIDER", "").strip().lower()
        if provider == "serpapi":
            return bool(os.getenv("SERPAPI_KEY"))
        if provider == "tavily":
            return bool(os.getenv("TAVILY_API_KEY"))
        return bool(os.getenv("SERPAPI_KEY") or os.getenv("TAVILY_API_KEY"))

    def _set_default_verdicts(self) -> None:
        claims = self.state.claims or [{"id": "s1", "c": self.state.claim or ""}]
        self.state.verdicts = [{"id": c.get("id", "s1"), "v": "insufficient", "conf": "low"} for c in claims]

    def _emit_step(
        self,
        step_callback: Optional[Callable[[Dict[str, Any]], None]],
        step_no: int,
        state_name: str,
        status: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        if step_callback is None:
            return
        if state_name == "OUTPUT" and self._task_name() == "gsm8k":
            explanation = "The agent produced final output for this math question."
            next_steps = "Next it will move to the next GSM8K sample."
        else:
            explanation, next_steps = _STAGE_MSG.get(state_name, _STAGE_MSG["OUTPUT"])
        step_callback(
            {
                "step": step_no,
                "state": state_name,
                "status": status,
                "explanation": explanation,
                "next_steps": next_steps,
                "detail": detail or {},
            }
        )

    def _parse_claim(self, claim: str) -> Dict[str, Any]:
        contract = (
            "Return JSON with keys: nc(str), ct(atomic|multi|question), sd(bool), subs(list). "
            "subs format: [{id:str,c:str}] with <=240 chars."
        )
        llm_out = self._call_llm_json(
            "parse_claim",
            contract,
            {"claim": claim, "st": self.state.fsm},
            max_tokens=220,
            include_controller=False,
        )
        if isinstance(llm_out, dict):
            nc = clean_text(str(llm_out.get("nc") or llm_out.get("normalized_claim") or llm_out.get("claim") or claim))[:240]
            subs_raw = llm_out.get("subs") if isinstance(llm_out.get("subs"), list) else llm_out.get("subclaims")
            subs = safe_claims(subs_raw, nc or claim)
            if llm_out.get("sd") is False:
                subs = [{"id": "s1", "c": nc or claim[:240]}]
            return {"nc": nc or claim[:240], "subs": subs, "via": "llm"}
        text = clean_text(claim)[:240]
        return {"nc": text, "subs": [{"id": "s1", "c": text}], "via": "default"}

    def _plan_queries(self, claims: List[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], str]:
        contract = "Return JSON: {plans:[{id:str,q:[str],lim:int}]}, 1..4 queries, each <=8 tokens."
        llm_out = self._call_llm_json("retrieval_planning", contract, {"claims": claims}, max_tokens=220)
        if not isinstance(llm_out, dict):
            out = []
            for c in claims:
                cid = str(c.get("id", "s1"))
                ctext = clean_text(str(c.get("c") or ""))[:96]
                out.append({"id": cid, "q": [ctext] if ctext else [], "lim": 4})
            return [x for x in out if x.get("q")], "default"

        claim_ids = {c.get("id") for c in claims}
        default_cid = str(claims[0].get("id", "s1")) if len(claims) == 1 else None
        plans_raw = first_list(llm_out, ["plans", "query_plan", "plan", "out"])
        if not plans_raw and default_cid:
            qsolo = first_list(llm_out, ["queries", "q"])
            if qsolo:
                plans_raw = [{"id": default_cid, "q": qsolo, "lim": llm_out.get("lim", 4)}]
        if not plans_raw:
            qmap = llm_out.get("queries") if isinstance(llm_out.get("queries"), dict) else llm_out
            if isinstance(qmap, dict):
                plans_raw = [{"id": str(cid), "q": qv, "lim": llm_out.get("lim", 4)} for cid, qv in qmap.items() if str(cid) in claim_ids]

        plans: List[Dict[str, Any]] = []
        for p in plans_raw:
            if isinstance(p, str) and default_cid:
                q = to_query_list(p)
                if q:
                    plans.append({"id": default_cid, "q": q, "lim": 4})
                continue
            if not isinstance(p, dict):
                continue
            cid = str(p.get("id") or p.get("claim_id") or p.get("cid") or (default_cid or "s1"))
            if cid not in claim_ids:
                if default_cid:
                    cid = default_cid
                else:
                    continue
            lim = coerce_int(p.get("lim", p.get("limit", p.get("k", 4))), default=4, lo=1, hi=10)
            qs = p.get("q")
            if qs is None:
                qs = p.get("queries") or p.get("query") or p.get("search_queries")
            q_list = to_query_list(qs)
            if not q_list and isinstance(p.get("terms"), list):
                q_list = to_query_list(" ".join([str(x) for x in p.get("terms", [])]))
            if not q_list and isinstance(p.get("keywords"), list):
                q_list = to_query_list(" ".join([str(x) for x in p.get("keywords", [])]))
            if q_list:
                plans.append({"id": cid, "q": q_list[:4], "lim": lim})

        if plans:
            return plans, "llm"
        out = []
        for c in claims:
            cid = str(c.get("id", "s1"))
            ctext = clean_text(str(c.get("c") or ""))[:96]
            out.append({"id": cid, "q": [ctext] if ctext else [], "lim": 4})
        return [x for x in out if x.get("q")], "default"

    def _arrange_retrieval_tools(
        self,
        claim_id: str,
        claim_text: str,
        query: str,
    ) -> Tuple[List[str], bool, int, str]:
        available: List[str] = []
        if self.network_enabled:
            available.append("search")
        if self._is_web_search_enabled():
            available.append("web_search")
        if not available:
            return [], False, 2, "default"

        contract = "Return JSON: {tools:[search|web_search],expand_pages:bool,top_n:int}"
        llm_out = self._call_llm_json(
            "retrieval_execution",
            contract,
            {
                "claim_id": claim_id,
                "claim": claim_text,
                "query": query,
                "available": available,
            },
            max_tokens=180,
        )
        if not isinstance(llm_out, dict):
            return available, True, self.top_n, "default"

        out_tools: List[str] = []
        raw_tools = llm_out.get("tools")
        if isinstance(raw_tools, list):
            for t in raw_tools:
                tt = str(t).strip().lower()
                if tt in available and tt not in out_tools:
                    out_tools.append(tt)
        if not out_tools:
            pick = str(llm_out.get("tool") or "").strip().lower()
            if pick in available:
                out_tools = [pick]
        if not out_tools:
            out_tools = available

        expand_pages = bool(llm_out.get("expand_pages")) if llm_out.get("expand_pages") is not None else True
        top_n = coerce_int(llm_out.get("top_n", self.top_n), default=self.top_n, lo=1, hi=8)
        return out_tools, expand_pages, top_n, "llm"

    def _extract_page_rows(self, base_rows: List[Dict[str, Any]], query: str, top_n: int) -> List[Dict[str, Any]]:
        out_rows: List[Dict[str, Any]] = []
        max_pages = self.wiki_fetch_limit
        if max_pages <= 0:
            return out_rows

        n_pages = 0
        for row in base_rows:
            if n_pages >= max_pages:
                break
            url = str(row.get("url") or "").strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                continue
            n_pages += 1
            fetched = self._run_tool_with_retry("page_fetch", {"url": url, "max_bytes": 180000, "timeout": 10}, retries=0)
            self.state.add_history("tool:page_fetch", fetched.get("s", "error"), {"url": url, "e": fetched.get("e")})
            if fetched.get("s") != "ok":
                continue
            text = str((fetched.get("d") or {}).get("text") or "")
            if not text:
                continue
            extracted = self._run_tool_with_retry("sentence_extract", {"text": text, "query": query, "top_n": top_n}, retries=0)
            self.state.add_history("tool:sentence_extract", extracted.get("s", "error"), {"url": url, "e": extracted.get("e")})
            if extracted.get("s") != "ok":
                continue
            for idx, item in enumerate((extracted.get("d") or {}).get("sentences", []), start=1):
                if not isinstance(item, dict):
                    continue
                sent = clean_text(str(item.get("s") or ""))
                if not sent:
                    continue
                out_rows.append(
                    {
                        "rid": f"{row.get('rid', 'r')}e{idx}",
                        "snippet": sent,
                        "url": url,
                        "src": "extract",
                        "d": row.get("d"),
                        "cred": "med",
                    }
                )
        return out_rows

    def _rows_to_evidence(self, rows: List[Dict[str, Any]], claim_id: str) -> List[EvidenceItem]:
        out: List[EvidenceItem] = []
        cred_default = {"wiki": "med", "web": "med", "news": "med", "extract": "med"}
        for idx, r in enumerate(rows, start=1):
            if not isinstance(r, dict):
                continue
            text = r.get("snippet") or r.get("title") or ""
            if not text:
                continue
            src = r.get("src", "web")
            rid = str(r.get("rid") or f"r{idx}")
            url = str(r.get("url") or src)
            out.append(
                EvidenceItem(
                    eid=f"{claim_id}:{src}:{rid}",
                    claim_id=claim_id,
                    s=" ".join(re.sub(r"<[^>]+>", " ", str(text)).split()),
                    src=url,
                    d=r.get("d"),
                    cred=r.get("cred") or cred_default.get(src, "med"),
                )
            )
        return out

    def _retrieve_for_query(self, claim_id: str, claim_text: str, query: str, lim: int) -> List[EvidenceItem]:
        tools, expand_pages, top_n, arranged_via = self._arrange_retrieval_tools(claim_id, claim_text, query)
        self.state.add_history(
            "llm:retrieval_execution",
            "ok",
            {"via": arranged_via, "tools": tools, "expand_pages": expand_pages, "top_n": top_n},
        )
        rows_collected: List[Dict[str, Any]] = []
        for tool_id in tools:
            args: Dict[str, Any] = {"q": query, "lim": lim}
            if tool_id == "search":
                args["src"] = "wiki"
            out = self._run_tool_with_retry(tool_id, args, retries=0)
            self.state.add_history(f"tool:{tool_id}", out.get("s", "error"), {"args": args, "e": out.get("e")})
            if out.get("s") != "ok":
                continue
            rows = extract_evidence_rows(out)
            if rows:
                rows_collected.extend(rows[:lim])
        if not rows_collected:
            return []
        if expand_pages:
            rows_collected.extend(self._extract_page_rows(rows_collected, query, top_n))
        return self._rows_to_evidence(rows_collected, claim_id)

    def _dedupe_evidence(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        out: List[EvidenceItem] = []
        seen: Set[str] = set()
        for item in items:
            key = (item.s or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(item)
        return out

    def _select_evidence(self, claims: List[Dict[str, str]], ev_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, str]], str]:
        select_cap = max(4, min(8, self.top_n * 2))
        contract = f"Return JSON: {{sel:[{{eid:str,for:str}}]}}. Select up to {select_cap} from provided evidence only."
        llm_out = self._call_llm_json("evidence_selection", contract, {"claims": claims, "evidence": ev_rows}, max_tokens=220)
        valid_eids = {e.get("eid") for e in ev_rows}
        claim_ids = {c.get("id") for c in claims}
        default_cid = claims[0].get("id", "s1") if len(claims) == 1 else None
        eid_to_claim = {str(e.get("eid")): str(e.get("for")) for e in ev_rows if isinstance(e, dict)}
        snippet_to_eid = {" ".join(str(e.get("s", "")).lower().split())[:120]: str(e.get("eid")) for e in ev_rows if isinstance(e, dict)}

        if not isinstance(llm_out, dict):
            picked: List[Dict[str, str]] = []
            by_claim: Dict[str, int] = {}
            for ev in ev_rows:
                cid = str(ev.get("for") or default_cid or "")
                eid = str(ev.get("eid") or "")
                if cid in claim_ids and eid and by_claim.get(cid, 0) < 2:
                    by_claim[cid] = by_claim.get(cid, 0) + 1
                    picked.append({"eid": eid, "for": cid})
                if len(picked) >= select_cap:
                    break
            return picked, "default"

        sel_raw = first_list(llm_out, ["sel", "selected", "evidence", "selected_evidence", "out"])
        out: List[Dict[str, str]] = []
        seen: Set[str] = set()
        for item in sel_raw:
            eid: Any = None
            cid: Any = None
            if isinstance(item, str):
                eid = item
                cid = eid_to_claim.get(str(eid), default_cid)
            elif isinstance(item, int):
                if 0 <= item < len(ev_rows):
                    eid = ev_rows[item].get("eid")
                    cid = ev_rows[item].get("for", default_cid)
            elif isinstance(item, dict):
                eid = item.get("eid") or item.get("id") or item.get("evidence_id")
                if not eid and isinstance(item.get("s"), str):
                    eid = snippet_to_eid.get(" ".join(item.get("s", "").lower().split())[:120])
                cid = item.get("for") or item.get("claim_id") or item.get("cid") or item.get("claim")
                if not cid:
                    cid = eid_to_claim.get(str(eid), default_cid)
            if cid not in claim_ids and default_cid:
                cid = default_cid
            if eid in valid_eids and cid in claim_ids and eid not in seen:
                seen.add(str(eid))
                out.append({"eid": str(eid), "for": str(cid)})

        if out:
            return out[:select_cap], "llm"
        return [], "default"

    def _assess_selection_progress(
        self,
        claims: List[Dict[str, str]],
        ev_rows: List[Dict[str, Any]],
        selected: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        contract = "Return JSON: {status:ok|back|retry,conf:low|med|high,reason:str}."
        selected_map = {str(s.get("eid")) for s in selected if isinstance(s, dict)}
        selected_rows = [e for e in ev_rows if str(e.get("eid")) in selected_map][: max(4, self.top_n)]
        llm_out = self._call_llm_json(
            "evidence_selection",
            contract,
            {
                "claims": claims,
                "target_top_n": self.top_n,
                "evidence_n": len(ev_rows),
                "selected_n": len(selected),
                "selected_rows": selected_rows,
            },
            max_tokens=160,
        )
        if isinstance(llm_out, dict):
            st = str(llm_out.get("status") or "").strip().lower()
            if st in {"ok", "back", "retry"}:
                conf = normalize_conf(llm_out.get("conf"))
                # Soft guardrail: a low-confidence "ok" with tiny selection should re-open selection/retrieval.
                if st == "ok" and conf == "low" and len(selected) < max(2, min(self.top_n, 3)) and len(ev_rows) >= self.top_n:
                    st = "retry"
                return {
                    "status": st,
                    "conf": conf,
                    "reason": clean_text(str(llm_out.get("reason") or ""))[:160],
                    "via": "llm",
                }
        if not selected:
            return {"status": "back", "conf": "low", "reason": "No selected evidence.", "via": "default"}
        min_sel = max(2, min(self.top_n, 3))
        if len(selected) < min_sel:
            if len(ev_rows) >= min_sel * 2:
                return {"status": "retry", "conf": "low", "reason": "Selection coverage is too small for current evidence.", "via": "default"}
            return {"status": "back", "conf": "low", "reason": "Need broader retrieval for better evidence.", "via": "default"}
        return {"status": "ok", "conf": "med", "reason": "Selected evidence available.", "via": "default"}

    def _assess_nli_progress(
        self,
        claims: List[Dict[str, str]],
        sel_rows: List[Dict[str, Any]],
        scores: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        contract = "Return JSON: {status:ok|back|retry,conf:low|med|high,reason:str}."
        summary = {"support": 0, "refute": 0, "neutral": 0, "high": 0, "med": 0, "low": 0}
        for s in scores:
            if not isinstance(s, dict):
                continue
            st = str(s.get("st") or "").strip().lower()
            cf = normalize_conf(s.get("conf"))
            if st in summary:
                summary[st] += 1
            summary[cf] += 1

        llm_out = self._call_llm_json(
            "nli_verification",
            contract,
            {
                "claims": claims,
                "target_top_n": self.top_n,
                "selected_n": len(sel_rows),
                "scores_n": len(scores),
                "summary": summary,
                "scores": scores[: max(4, self.top_n)],
                "gate_policy": [
                    "If scores are mostly neutral+low confidence, choose back.",
                    "If stance coverage is weak or ambiguous for decision, choose back.",
                    "Use ok only when score quality is sufficient for verdict decision.",
                ],
            },
            max_tokens=160,
            include_controller=True,
        )
        if isinstance(llm_out, dict):
            st = str(llm_out.get("status") or "").strip().lower()
            if st in {"ok", "back", "retry"}:
                conf = normalize_conf(llm_out.get("conf"))
                # Soft guardrail: avoid advancing on uniformly weak neutral signals.
                if st == "ok" and conf == "low" and summary["support"] == 0 and summary["refute"] == 0:
                    st = "back"
                return {
                    "status": st,
                    "conf": conf,
                    "reason": clean_text(str(llm_out.get("reason") or ""))[:160],
                    "via": "llm",
                }

        if not scores:
            return {"status": "back", "conf": "low", "reason": "No NLI scores.", "via": "default"}
        if summary["support"] == 0 and summary["refute"] == 0 and summary["high"] == 0 and summary["med"] <= 1:
            return {"status": "back", "conf": "low", "reason": "Only weak neutral NLI scores.", "via": "default"}
        return {"status": "ok", "conf": "med", "reason": "NLI scores available.", "via": "default"}

    def _nli_scores(self, claims: List[Dict[str, str]], sel_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, str]], str]:
        contract = "Return JSON: {scores:[{eid:str,for:str,st:support|refute|neutral,conf:low|med|high}]}"
        llm_out = self._call_llm_json(
            "nli_verification",
            contract,
            {"claims": claims, "selected": sel_rows},
            max_tokens=280,
            include_controller=False,
        )
        valid_eids = {r.get("eid") for r in sel_rows}
        claim_ids = {c.get("id") for c in claims}
        default_cid = claims[0].get("id", "s1") if len(claims) == 1 else None
        eid_to_claim = {str(r.get("eid")): str(r.get("for")) for r in sel_rows if isinstance(r, dict)}
        claim_to_eids: Dict[str, List[str]] = {}
        for r in sel_rows:
            if isinstance(r, dict):
                cid, eid = str(r.get("for", "")), str(r.get("eid", ""))
                if cid and eid:
                    claim_to_eids.setdefault(cid, []).append(eid)

        if not isinstance(llm_out, dict):
            default_scores = []
            for row in sel_rows:
                if not isinstance(row, dict):
                    continue
                default_scores.append(
                    {
                        "eid": str(row.get("eid") or ""),
                        "for": str(row.get("for") or default_cid or "s1"),
                        "st": "neutral",
                        "conf": "low",
                    }
                )
            return default_scores, "default"

        scores_raw = first_list(llm_out, ["scores", "results", "nli", "labels", "classifications", "out"])
        out: List[Dict[str, str]] = []
        seen_pairs: Set[str] = set()
        for item in scores_raw:
            if not isinstance(item, dict):
                continue
            eid = item.get("eid") or item.get("id") or item.get("evidence_id")
            cid = item.get("for") or item.get("claim_id") or item.get("cid") or item.get("claim")
            st = normalize_stance(item.get("st") or item.get("stance") or item.get("label") or item.get("verdict") or item.get("nli"))
            conf = normalize_conf(item.get("conf") or item.get("confidence") or item.get("score"))
            if not cid:
                cid = eid_to_claim.get(str(eid), default_cid)
            if cid not in claim_ids and default_cid:
                cid = default_cid
            if cid not in claim_ids:
                continue
            if eid not in valid_eids:
                eids = claim_to_eids.get(str(cid), [])
                if len(eids) == 1:
                    eid = eids[0]
                else:
                    continue
            if not st:
                continue
            key = f"{eid}::{cid}"
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            out.append({"eid": str(eid), "for": str(cid), "st": st, "conf": conf})

        if out:
            return out, "llm"
        default_scores = []
        for row in sel_rows:
            if not isinstance(row, dict):
                continue
            default_scores.append(
                {
                    "eid": str(row.get("eid") or ""),
                    "for": str(row.get("for") or default_cid or "s1"),
                    "st": "neutral",
                    "conf": "low",
                }
            )
        return default_scores, "default"

    def _decide(self, claims: List[Dict[str, str]], scores: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str]:
        contract = "Return JSON: {ver:[{id:str,v:supported|refuted|mixed|insufficient,conf:low|med|high}]}"
        llm_out = self._call_llm_json("verdict_decision", contract, {"claims": claims, "scores": scores}, max_tokens=200)
        claim_ids = {c.get("id") for c in claims}
        default_cid = claims[0].get("id", "s1") if len(claims) == 1 else None
        if not isinstance(llm_out, dict):
            return [{"id": str(c.get("id", "s1")), "v": "insufficient", "conf": "low"} for c in claims], "default"

        ver_raw = first_list(llm_out, ["ver", "verdicts", "decisions", "judgments", "out"])
        if not ver_raw:
            single = first_dict(llm_out, ["ver", "verdicts"])
            if single:
                ver_raw = [single]
            elif {"id", "v"}.issubset(set(llm_out.keys())):
                ver_raw = [llm_out]
            elif any(str(k) in claim_ids for k in llm_out.keys()):
                ver_raw = []
                for cid_key, value in llm_out.items():
                    cid_key = str(cid_key)
                    if cid_key not in claim_ids:
                        continue
                    if isinstance(value, dict):
                        ver_raw.append({"id": cid_key, **value})
                    else:
                        ver_raw.append({"id": cid_key, "v": value})

        out: List[Dict[str, str]] = []
        seen: Set[str] = set()
        for item in ver_raw:
            if isinstance(item, str) and default_cid:
                cid = default_cid
                vv = normalize_verdict(item)
                cc = "med"
            elif isinstance(item, dict):
                cid = item.get("id") or item.get("claim_id") or item.get("cid") or default_cid
                vv = normalize_verdict(item.get("v") or item.get("verdict") or item.get("label") or item.get("decision"))
                cc = normalize_conf(item.get("conf") or item.get("confidence") or item.get("score"))
            else:
                continue
            if cid not in claim_ids and default_cid:
                cid = default_cid
            if cid in claim_ids and vv and cid not in seen:
                seen.add(str(cid))
                out.append({"id": str(cid), "v": vv, "conf": cc})

        if out:
            return out, "llm"
        return [{"id": str(c.get("id", "s1")), "v": "insufficient", "conf": "low"} for c in claims], "default"

    def _compose_output(self, claims: List[Dict[str, str]], verdicts: List[Dict[str, str]], selected: List[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], str]:
        contract = (
            "Return JSON: {out:[{id:str,ver:supported|refuted|mixed|insufficient,conf:low|med|high,r:str,cite:[str]}]}, "
            "with rationale <=220 chars."
        )
        llm_out = self._call_llm_json("response_output", contract, {"claims": claims, "verdicts": verdicts, "selected": selected}, max_tokens=260)
        claim_ids = {c.get("id") for c in claims}
        default_cid = claims[0].get("id", "s1") if len(claims) == 1 else None
        if not isinstance(llm_out, dict):
            verdict_map = {str(v.get("id")): v for v in verdicts if isinstance(v, dict)}
            cite_map: Dict[str, List[str]] = {}
            for s in selected:
                if isinstance(s, dict):
                    cid = str(s.get("for") or "")
                    eid = str(s.get("eid") or "")
                    if cid and eid:
                        cite_map.setdefault(cid, []).append(eid)
            rows = []
            for c in claims:
                cid = str(c.get("id", "s1"))
                vv = verdict_map.get(cid, {"v": "insufficient", "conf": "low"})
                rows.append(
                    {
                        "id": cid,
                        "ver": str(vv.get("v", "insufficient")),
                        "conf": normalize_conf(vv.get("conf")),
                        "r": "LLM output unavailable; conservative verdict.",
                        "cite": cite_map.get(cid, [])[:2],
                    }
                )
            return rows, "default"

        out_raw = first_list(llm_out, ["out", "output", "final"])
        if not out_raw:
            single = first_dict(llm_out, ["out", "output"])
            if single:
                out_raw = [single]
            elif {"id", "ver"}.issubset(set(llm_out.keys())) or {"id", "v"}.issubset(set(llm_out.keys())):
                out_raw = [llm_out]

        out: List[Dict[str, Any]] = []
        for item in out_raw:
            if not isinstance(item, dict):
                continue
            cid = item.get("id") or item.get("claim_id") or item.get("cid") or default_cid
            vv = normalize_verdict(item.get("ver") or item.get("v") or item.get("verdict") or item.get("label"))
            cc = normalize_conf(item.get("conf") or item.get("confidence"))
            rr = item.get("r") or item.get("reason") or item.get("rationale") or ""
            cite = item.get("cite", item.get("citations", []))
            if cid not in claim_ids and default_cid:
                cid = default_cid
            if cid not in claim_ids or not vv:
                continue
            if not isinstance(rr, str):
                rr = ""
            if not isinstance(cite, list):
                cite = []
            out.append({"id": str(cid), "ver": vv, "conf": cc, "r": rr[:220], "cite": [str(x) for x in cite[:2]]})

        if out:
            return out, "llm"
        verdict_map = {str(v.get("id")): v for v in verdicts if isinstance(v, dict)}
        rows = []
        for c in claims:
            cid = str(c.get("id", "s1"))
            vv = verdict_map.get(cid, {"v": "insufficient", "conf": "low"})
            rows.append({"id": cid, "ver": vv.get("v", "insufficient"), "conf": normalize_conf(vv.get("conf")), "r": "", "cite": []})
        return rows, "default"

    def _run_fever(self, claim: str, step_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        self.state.claim = claim
        retries: Dict[str, int] = {}
        step_no = 0

        while step_no < self.max_steps:
            step_no += 1
            current = self.state.fsm

            if current == "PARSE_CLAIM":
                parsed = self._parse_claim(claim)
                self.state.norm_claim = parsed.get("nc")
                self.state.claims = safe_claims(parsed.get("subs"), parsed.get("nc", claim))
                detail = {"via": parsed.get("via"), "n_claims": len(self.state.claims)}
                self.state.add_history("llm:parse_claim", "ok", detail)
                self._emit_step(step_callback, step_no, current, "ok", detail)
                self._advance("ok")
                continue

            if current == "RETRIEVAL":
                plans, via = self._plan_queries(self.state.claims)
                self.state.plans = plans
                self.state.add_history("llm:retrieval_plan", "ok", {"via": via, "n_plans": len(plans)})
                collected: List[EvidenceItem] = []
                n_queries = 0
                claim_map = {str(c.get("id", "s1")): str(c.get("c") or "") for c in self.state.claims if isinstance(c, dict)}
                for p in plans:
                    cid = str(p.get("id", "s1"))
                    claim_text = claim_map.get(cid, self.state.norm_claim or claim)
                    lim = p.get("lim", 4)
                    for q in p.get("q", []):
                        n_queries += 1
                        collected.extend(self._retrieve_for_query(cid, claim_text, q, lim))
                collected = self._dedupe_evidence(collected)
                self.state.evidence = collected
                if collected:
                    self._emit_step(step_callback, step_no, current, "ok", {"via": via, "queries": n_queries, "evidence_n": len(collected)})
                    self._advance("ok")
                    continue
                tries = retries.get("RETRIEVAL_EMPTY", 0) + 1
                retries["RETRIEVAL_EMPTY"] = tries
                status = "retry" if tries <= self.n_retry else "error"
                self.state.add_history("retrieval_empty", status, {"tries": tries, "queries": n_queries})
                self._emit_step(step_callback, step_no, current, status, {"tries": tries, "queries": n_queries})
                if status == "retry":
                    self._advance("retry")
                    continue
                self._advance("error")
                continue

            if current == "SELECT_EVIDENCE":
                ev_in = [{"eid": e.eid, "for": e.claim_id, "s": e.s, "src": e.src, "d": e.d, "cred": e.cred} for e in self.state.evidence]
                if not ev_in:
                    tries = retries.get("SELECT_NO_EVIDENCE", 0) + 1
                    retries["SELECT_NO_EVIDENCE"] = tries
                    status = "back" if tries <= self.n_retry else "error"
                    self.state.selected = []
                    self.state.add_history("select_no_evidence", status, {"tries": tries})
                    self._emit_step(step_callback, step_no, current, status, {"reason": "no_evidence", "tries": tries})
                    if status == "back":
                        self._advance("back")
                        continue
                    self._advance("error")
                    continue
                selected, via = self._select_evidence(self.state.claims, ev_in)
                if selected:
                    self.state.selected = selected
                    gate = self._assess_selection_progress(self.state.claims, ev_in, selected)
                    detail = {"via": via, "selected_n": len(selected), "gate": gate}
                    gate_status = str(gate.get("status") or "ok")
                    if gate_status == "ok":
                        self.state.add_history("llm:evidence_selection", "ok", detail)
                        self._emit_step(step_callback, step_no, current, "ok", detail)
                        self._advance("ok")
                        continue

                    tries = retries.get("SELECT_GATE", 0) + 1
                    retries["SELECT_GATE"] = tries
                    self.state.add_history("select_gate", gate_status, {"tries": tries, "gate": gate})
                    self._emit_step(step_callback, step_no, current, gate_status, {"tries": tries, "gate": gate})
                    if gate_status == "back" and tries <= self.n_retry:
                        self._advance("back")
                        continue
                    if gate_status == "retry" and tries <= self.n_retry:
                        self._advance("retry")
                        continue
                    self.state.add_history("select_gate_exhausted", "ok", {"tries": tries})
                    self._advance("ok")
                    continue
                tries = retries.get("SELECT_EMPTY", 0) + 1
                retries["SELECT_EMPTY"] = tries
                status = "back" if tries <= self.n_retry else "error"
                self.state.add_history("select_empty", status, {"tries": tries})
                self._emit_step(step_callback, step_no, current, status, {"tries": tries})
                if status == "back":
                    self._advance("back")
                    continue
                self.state.selected = []
                self._advance("error")
                continue

            if current == "NLI_VERIFY":
                selected_ids = {s.get("eid") for s in self.state.selected}
                sel_rows = [
                    {"eid": e.eid, "for": e.claim_id, "s": (e.s or "")[:280], "cred": e.cred}
                    for e in self.state.evidence
                    if e.eid in selected_ids
                ]
                if not sel_rows:
                    tries = retries.get("NLI_NO_SELECTED", 0) + 1
                    retries["NLI_NO_SELECTED"] = tries
                    status = "back" if tries <= self.n_retry else "error"
                    self.state.scores = []
                    self.state.add_history("nli_no_selected", status, {"tries": tries})
                    self._emit_step(step_callback, step_no, current, status, {"reason": "no_selected_rows", "tries": tries})
                    if status == "back":
                        self._advance("back")
                        continue
                    self._advance("error")
                    continue
                scores, via = self._nli_scores(self.state.claims, sel_rows)
                if scores:
                    self.state.scores = scores
                    gate = self._assess_nli_progress(self.state.claims, sel_rows, scores)
                    detail = {"via": via, "scores_n": len(scores), "gate": gate}
                    gate_status = str(gate.get("status") or "ok")
                    if gate_status == "ok":
                        self.state.add_history("llm:nli_verify", "ok", detail)
                        self._emit_step(step_callback, step_no, current, "ok", detail)
                        self._advance("ok")
                        continue

                    tries = retries.get("NLI_GATE", 0) + 1
                    retries["NLI_GATE"] = tries
                    self.state.add_history("nli_gate", gate_status, {"tries": tries, "gate": gate})
                    self._emit_step(step_callback, step_no, current, gate_status, {"tries": tries, "gate": gate})
                    if gate_status == "back" and tries <= self.n_retry:
                        self._advance("back")
                        continue
                    if gate_status == "retry" and tries <= self.n_retry:
                        self._advance("retry")
                        continue
                    self.state.add_history("nli_gate_exhausted", "ok", {"tries": tries})
                    self._advance("ok")
                    continue
                tries = retries.get("NLI_EMPTY", 0) + 1
                retries["NLI_EMPTY"] = tries
                status = "back" if tries <= self.n_retry else "error"
                self.state.scores = []
                self.state.add_history("nli_empty", status, {"tries": tries})
                self._emit_step(step_callback, step_no, current, status, {"reason": "nli_empty", "tries": tries})
                if status == "back":
                    self._advance("back")
                    continue
                self._advance("error")
                continue

            if current == "DECIDE":
                verdicts, via = self._decide(self.state.claims, self.state.scores)
                self.state.verdicts = verdicts or self.state.verdicts
                if not self.state.verdicts:
                    self._set_default_verdicts()
                    via = "fallback"
                detail = {"via": via, "verdicts_n": len(self.state.verdicts)}
                self.state.add_history("llm:decide", "ok", detail)
                self._emit_step(step_callback, step_no, current, "ok", detail)
                self._advance("ok")
                continue

            if current == "OUTPUT":
                if not self.state.verdicts:
                    self._set_default_verdicts()
                out_rows, via = self._compose_output(self.state.claims, self.state.verdicts, self.state.selected)
                result = {"s": "ok", "d": {"out": out_rows}, "e": None, "rb": "none"}
                self.state.output = result["d"]
                detail = {"via": via, "out_n": len(out_rows)}
                self.state.add_history("llm:output", "ok", detail)
                self._emit_step(step_callback, step_no, current, "ok", detail)
                return result

            self._set_default_verdicts()
            self._emit_step(step_callback, step_no, current, "error", {"reason": "unknown_state"})
            self._advance("error")

        self._set_default_verdicts()
        claims = self.state.claims or [{"id": "s1", "c": claim}]
        out_rows, _ = self._compose_output(claims, self.state.verdicts, self.state.selected)
        return {"s": "ok", "d": {"out": out_rows}, "e": None, "rb": "none"}

    def _coerce_float(self, value: Any) -> Optional[float]:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value or "").strip()
        if not text:
            return None
        text = text.replace(",", "")
        m = re.search(r"-?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None

    def _parse_problem(self, question: str) -> Dict[str, Any]:
        contract = "Return JSON: {nq:str,target:str,givens:[str],unit:str}."
        llm_out = self._call_llm_json(
            "parse_math_problem",
            contract,
            {"question": question, "st": self.state.fsm},
            max_tokens=260,
            include_controller=False,
        )
        if isinstance(llm_out, dict):
            nq = clean_text(str(llm_out.get("nq") or llm_out.get("normalized_question") or question))[:320]
            target = clean_text(str(llm_out.get("target") or llm_out.get("goal") or ""))[:220]
            givens_raw = llm_out.get("givens", [])
            givens: List[str] = []
            if isinstance(givens_raw, list):
                for g in givens_raw:
                    gg = clean_text(str(g))
                    if gg:
                        givens.append(gg[:180])
            unit = clean_text(str(llm_out.get("unit") or ""))[:80]
            return {"nq": nq, "target": target, "givens": givens[:8], "unit": unit, "via": "llm"}
        return {"nq": clean_text(question)[:320], "target": "", "givens": [], "unit": "", "via": "fallback"}

    def _plan_solution(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        contract = "Return JSON: {plan:[str],checks:[str]}; plan length 2..6."
        llm_out = self._call_llm_json("plan_math_solution", contract, parsed, max_tokens=280)
        if isinstance(llm_out, dict):
            plan_raw = llm_out.get("plan")
            checks_raw = llm_out.get("checks")
            plan = [clean_text(str(x))[:180] for x in plan_raw] if isinstance(plan_raw, list) else []
            checks = [clean_text(str(x))[:180] for x in checks_raw] if isinstance(checks_raw, list) else []
            plan = [p for p in plan if p]
            checks = [c for c in checks if c]
            if plan:
                return {"plan": plan[:6], "checks": checks[:3], "via": "llm"}
        return {"plan": ["Compute the required quantity directly from the givens."], "checks": [], "via": "fallback"}

    def _tool_result_brief(self, tool_id: str, out: Dict[str, Any]) -> Dict[str, Any]:
        data = out.get("d") if isinstance(out, dict) else {}
        if not isinstance(data, dict):
            return {"ok": False}
        if tool_id == "math_eval":
            return {"ok": True, "value": data.get("value")}
        if tool_id == "math_check":
            return {"ok": True, "match": data.get("match"), "delta": data.get("delta")}
        return {"ok": True}

    def _normalize_math_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(action, dict):
            return {}
        out = dict(action)
        a_raw = str(out.get("a") or out.get("action") or "").strip().lower()
        if not a_raw:
            if out.get("tool"):
                a_raw = "tool"
            elif any(k in out for k in ["ans", "answer", "reasoning", "conf"]):
                a_raw = "finish"
        if a_raw in {"final", "done", "answer", "output"}:
            a_raw = "finish"
        if a_raw in {"call_tool", "use_tool", "tool_call"}:
            a_raw = "tool"
        if a_raw in {"plan", "think", "reason"}:
            a_raw = "tool"
        out["a"] = a_raw

        tool_raw = str(out.get("tool") or out.get("name") or out.get("t") or "").strip().lower()
        if tool_raw in {"calc", "calculator", "evaluate", "eval"}:
            tool_raw = "math_eval"
        if tool_raw in {"check", "verify", "compare"}:
            tool_raw = "math_check"
        if tool_raw:
            out["tool"] = tool_raw

        if "ans" not in out and "answer" in out:
            out["ans"] = out.get("answer")
        return out

    def _execute_solution_direct(self, question: str, parsed: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        contract = "Return JSON: {reasoning:str,ans:number|string,unit:str,conf:low|med|high}."
        llm_out = self._call_llm_json(
            "execute_math_solution",
            contract,
            {"question": question, "parsed": parsed, "plan": plan},
            max_tokens=420,
            include_controller=False,
        )
        if isinstance(llm_out, dict):
            ans = self._coerce_float(llm_out.get("ans"))
            reasoning = clean_text(str(llm_out.get("reasoning") or llm_out.get("r") or ""))[:420]
            conf = normalize_conf(llm_out.get("conf"))
            unit = clean_text(str(llm_out.get("unit") or parsed.get("unit") or ""))[:80]
            if ans is not None:
                return {"ans": ans, "reasoning": reasoning, "conf": conf, "unit": unit, "via": "llm"}
        return {"ans": None, "reasoning": "", "conf": "low", "unit": clean_text(str(parsed.get("unit") or ""))[:80], "via": "fallback"}

    def _execute_solution(self, question: str, parsed: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        allowed_tools = skill_registry.tools_for_state(self.state.fsm, task=self._task_name())
        observations: List[Dict[str, Any]] = []
        seed_solved: Optional[Dict[str, Any]] = None

        contract = (
            "Return JSON action. "
            "Tool mode: {a:'tool',tool:'math_eval|math_check',args:object}. "
            "Finish mode: {a:'finish',ans:number|string,reasoning:str,conf:low|med|high}."
        )
        for turn in range(self.max_math_tool_calls):
            payload = {
                "question": question,
                "parsed": parsed,
                "plan": plan,
                "obs": observations[-4:],
                "turn": turn + 1,
                "remaining_tool_calls": self.max_math_tool_calls - turn,
            }
            action = self._call_llm_json("math_tool_use", contract, payload, max_tokens=260)
            if not isinstance(action, dict):
                break
            action = self._normalize_math_action(action)

            if action.get("a") == "tool":
                if not action.get("tool"):
                    repair = self._call_llm_json(
                        "math_tool_use",
                        "Return JSON: {tool:'math_eval|math_check',args:object}.",
                        payload,
                        max_tokens=120,
                    )
                    if isinstance(repair, dict):
                        repair = self._normalize_math_action(repair)
                        if repair.get("tool"):
                            action["tool"] = repair.get("tool")
                        if isinstance(repair.get("args"), dict):
                            action["args"] = repair.get("args")
                if str(action.get("tool")) == "math_eval":
                    args = action.get("args")
                    if not isinstance(args, dict):
                        args = {}
                    expr = args.get("expr")
                    if not isinstance(expr, str) or not expr.strip():
                        expr_out = self._call_llm_json(
                            "execute_math_solution",
                            "Return JSON: {expr:str}. Expression must be arithmetic only.",
                            payload,
                            max_tokens=120,
                            include_controller=False,
                        )
                        if isinstance(expr_out, dict):
                            expr = expr_out.get("expr")
                        if not isinstance(expr, str) or not expr.strip():
                            if seed_solved is None:
                                seed_solved = self._execute_solution_direct(question, parsed, plan)
                            seed_ans = seed_solved.get("ans") if isinstance(seed_solved, dict) else None
                            expr = str(seed_ans) if seed_ans is not None else ""
                    action["args"] = {"expr": str(expr).strip(), "vars": args.get("vars", {})}

            ok, msg = check_action_payload(action, allowed_tools)
            if not ok:
                self.state.add_history(
                    "llm:math_tool_action_invalid",
                    "retry",
                    {"msg": msg[:120], "action": list(action.keys())[:8], "a": str(action.get("a"))[:40]},
                )
                break

            act = action.get("a")
            if act == "tool":
                tool_id = str(action.get("tool"))
                args = action.get("args")
                if not isinstance(args, dict):
                    args = {}
                self.state.tool_requests.append({"id": f"mt{len(self.state.tool_requests) + 1}", "tool": tool_id, "args": args, "for": "q1"})
                out = self._run_tool_with_retry(tool_id, args, retries=0)
                self.state.add_history(f"tool:{tool_id}", out.get("s", "error"), {"args": args, "e": out.get("e")})
                brief = self._tool_result_brief(tool_id, out)
                brief.update({"tool": tool_id})
                observations.append(brief)
                continue

            if act == "finish":
                if not observations and allowed_tools:
                    observations.append({"ok": False, "policy": "call_one_tool_before_finish"})
                    self.state.add_history("llm:math_tool_policy", "retry", {"msg": "finish_without_tool"})
                    continue
                ans = self._coerce_float(action.get("ans"))
                reasoning = clean_text(str(action.get("reasoning") or action.get("r") or ""))[:420]
                conf = normalize_conf(action.get("conf"))
                if ans is not None:
                    used_tools = any(isinstance(ob, dict) and ob.get("tool") for ob in observations)
                    via = "llm+tools" if used_tools else "llm"
                    return {"ans": ans, "reasoning": reasoning, "conf": conf, "unit": clean_text(str(parsed.get("unit") or ""))[:80], "via": via}
                break

        for ob in reversed(observations):
            if not isinstance(ob, dict):
                continue
            val = self._coerce_float(ob.get("value"))
            if val is not None:
                return {
                    "ans": val,
                    "reasoning": "Answer taken from math_eval tool output.",
                    "conf": "med",
                    "unit": clean_text(str(parsed.get("unit") or ""))[:80],
                    "via": "tool_fallback",
                }

        solved = self._execute_solution_direct(question, parsed, plan)
        tool_obs_n = sum(1 for ob in observations if isinstance(ob, dict) and ob.get("tool"))
        if tool_obs_n > 0:
            solved["tool_obs_n"] = tool_obs_n
            if solved.get("via") == "llm":
                solved["via"] = "llm_after_tools"
        return solved

    def _verify_solution(self, question: str, parsed: Dict[str, Any], plan: Dict[str, Any], solved: Dict[str, Any]) -> Dict[str, Any]:
        contract = "Return JSON: {ok:bool,ans:number|string,notes:str,conf:low|med|high}."
        llm_out = self._call_llm_json(
            "verify_math_solution",
            contract,
            {"question": question, "parsed": parsed, "plan": plan, "solved": solved},
            max_tokens=260,
            include_controller=False,
        )
        if isinstance(llm_out, dict):
            ans = self._coerce_float(llm_out.get("ans"))
            ok = bool(llm_out.get("ok")) if llm_out.get("ok") is not None else False
            notes = clean_text(str(llm_out.get("notes") or ""))[:220]
            conf = normalize_conf(llm_out.get("conf") or solved.get("conf"))
            if ans is not None:
                return {"ans": ans, "ok": ok, "notes": notes, "conf": conf, "via": "llm"}
        return {"ans": solved.get("ans"), "ok": False, "notes": "No structured verification output.", "conf": solved.get("conf", "low"), "via": "fallback"}

    def _compose_math_output(self, question: str, verified: Dict[str, Any], solved: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        contract = "Return JSON: {out:[{id:str,answer:number|string,conf:low|med|high,r:str}]}"
        llm_out = self._call_llm_json(
            "math_output",
            contract,
            {"question": question, "verified": verified, "solved": solved},
            max_tokens=220,
        )
        if isinstance(llm_out, dict):
            out_raw = first_list(llm_out, ["out", "output", "final"])
            rows: List[Dict[str, Any]] = []
            for item in out_raw:
                if not isinstance(item, dict):
                    continue
                answer = self._coerce_float(item.get("answer"))
                if answer is None:
                    answer = self._coerce_float(item.get("ans"))
                conf = normalize_conf(item.get("conf") or verified.get("conf"))
                rationale = clean_text(str(item.get("r") or item.get("reason") or item.get("rationale") or ""))[:220]
                if answer is None:
                    continue
                rows.append({"id": str(item.get("id") or "q1"), "answer": answer, "conf": conf, "r": rationale})
            if rows:
                return rows, "llm"

        ans = verified.get("ans")
        if ans is None:
            ans = solved.get("ans")
        if ans is None:
            ans = 0.0
        row = {
            "id": "q1",
            "answer": float(ans),
            "conf": normalize_conf(verified.get("conf") or solved.get("conf")),
            "r": clean_text(str(verified.get("notes") or solved.get("reasoning") or "Fallback math output."))[:220],
        }
        return [row], "fallback"

    def _run_gsm(self, question: str, step_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        self.state.claim = question
        self.state.tool_requests = []
        step_no = 0
        parsed: Dict[str, Any] = {}
        plan: Dict[str, Any] = {}
        solved: Dict[str, Any] = {}
        verified: Dict[str, Any] = {}

        while step_no < self.max_steps:
            step_no += 1
            current = self.state.fsm

            if current == "PARSE_PROBLEM":
                parsed = self._parse_problem(question)
                self.state.norm_claim = parsed.get("nq")
                self.state.claims = [{"id": "q1", "c": question}]
                detail = {"via": parsed.get("via"), "givens_n": len(parsed.get("givens", []))}
                self.state.add_history("llm:parse_problem", "ok", detail)
                self._emit_step(step_callback, step_no, current, "ok", detail)
                self._advance("ok")
                continue

            if current == "PLAN_SOLUTION":
                plan = self._plan_solution(parsed)
                self.state.plans = [{"id": "q1", "steps": plan.get("plan", []), "checks": plan.get("checks", [])}]
                detail = {"via": plan.get("via"), "steps_n": len(plan.get("plan", []))}
                self.state.add_history("llm:plan_solution", "ok", detail)
                self._emit_step(step_callback, step_no, current, "ok", detail)
                self._advance("ok")
                continue

            if current == "EXECUTE_SOLUTION":
                n_tools_before = len(self.state.tool_requests)
                solved = self._execute_solution(question, parsed, plan)
                self.state.scores = [{"id": "q1", "answer": solved.get("ans"), "conf": solved.get("conf")}]
                if solved.get("ans") is None:
                    self.state.add_history("math:execute_empty", "error", {"via": solved.get("via")})
                    self._emit_step(step_callback, step_no, current, "error", {"via": solved.get("via")})
                    self._advance("error")
                    continue
                detail = {
                    "via": solved.get("via"),
                    "conf": solved.get("conf"),
                    "tool_calls": max(0, len(self.state.tool_requests) - n_tools_before),
                }
                self.state.add_history("llm:execute_solution", "ok", detail)
                self._emit_step(step_callback, step_no, current, "ok", detail)
                self._advance("ok")
                continue

            if current == "VERIFY_SOLUTION":
                verified = self._verify_solution(question, parsed, plan, solved)
                detail = {"via": verified.get("via"), "ok": verified.get("ok"), "conf": verified.get("conf")}
                self.state.add_history("llm:verify_solution", "ok", detail)
                self._emit_step(step_callback, step_no, current, "ok", detail)
                self._advance("ok")
                continue

            if current == "OUTPUT":
                out_rows, via = self._compose_math_output(question, verified, solved)
                result = {"s": "ok", "d": {"out": out_rows}, "e": None, "rb": "none"}
                self.state.output = result["d"]
                detail = {"via": via, "out_n": len(out_rows)}
                self.state.add_history("llm:math_output", "ok", detail)
                self._emit_step(step_callback, step_no, current, "ok", detail)
                return result

            self._emit_step(step_callback, step_no, current, "error", {"reason": "unknown_state"})
            self._advance("error")

        out_rows, via = self._compose_math_output(question, verified, solved)
        self.state.output = {"out": out_rows}
        self.state.add_history("math:max_steps", "error", {"via": via})
        return {"s": "ok", "d": {"out": out_rows}, "e": None, "rb": "none"}

    def run(self, text: str, step_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        task_name = self._task_name()
        if task_name == "gsm8k":
            return self._run_gsm(text, step_callback=step_callback)
        return self._run_fever(text, step_callback=step_callback)


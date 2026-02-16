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
from guardrail import check_tool_output, extract_evidence_rows, extract_json_object
from orchestrator_helpers import (
    STOPWORDS,
    clean_text,
    coerce_int,
    env_int,
    fallback_decide,
    fallback_nli,
    fallback_output,
    fallback_parse,
    fallback_query_plans,
    fallback_select,
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
        "The agent is collecting candidate evidence from search/KB tools.",
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
        self.subskill_hint_chars = max(500, env_int(os.getenv,"SUBSKILL_HINT_CHARS", 1000))
        self.controller_hint_chars = max(300, env_int(os.getenv,"CONTROLLER_HINT_CHARS", 700))
        self.controller_skill = load_text(skill_registry.SKILLS["fsm_fact_verification"]["path"])
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

    def _controller_hint(self, max_chars: Optional[int] = None) -> str:
        text = (self.controller_skill or "").strip()
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
        system = (
            "You are an FSM fact-verification sub-agent under soft constraints. "
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
        self.state.tick(fsm_next_state(self.state.fsm, status))

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

    def _fallback_parse(self, claim: str) -> Dict[str, Any]:
        return fallback_parse(claim)

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
        fb = self._fallback_parse(claim)
        subs = safe_claims(fb.get("subs"), fb.get("nc", claim)) if fb.get("sd") else [{"id": "s1", "c": fb.get("nc", claim)}]
        return {"nc": fb.get("nc", claim), "subs": subs, "via": "fallback"}

    def _fallback_query_plans(self, claims: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        return fallback_query_plans(claims)

    def _plan_queries(self, claims: List[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], str]:
        contract = "Return JSON: {plans:[{id:str,q:[str],lim:int}]}, 1..4 queries, each <=8 tokens."
        llm_out = self._call_llm_json("retrieval_planning", contract, {"claims": claims}, max_tokens=220)
        if not isinstance(llm_out, dict):
            return self._fallback_query_plans(claims), "fallback"

        claim_ids = {c.get("id") for c in claims}
        default_cid = claims[0].get("id", "s1") if len(claims) == 1 else None
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
        self._llm_schema_mismatch("retrieval_planning", llm_out)
        return self._fallback_query_plans(claims), "fallback"

    def _query_overlap_ok(self, query: str, rows: List[Dict[str, Any]]) -> bool:
        q_terms = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in STOPWORDS}
        if not q_terms:
            return True
        best = 0
        for r in rows:
            txt = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
            t_terms = {t for t in re.findall(r"[a-z0-9]+", txt) if t not in STOPWORDS}
            best = max(best, len(q_terms.intersection(t_terms)))
        return best >= (1 if len(q_terms) <= 3 else 2)

    def _rows_to_evidence(self, rows: List[Dict[str, Any]], claim_id: str) -> List[EvidenceItem]:
        out: List[EvidenceItem] = []
        cred_default = {"wiki": "low", "web": "low", "news": "low", "kb": "med", "extract": "med"}
        for r in rows:
            if not isinstance(r, dict):
                continue
            text = r.get("snippet") or r.get("title") or ""
            if not text:
                continue
            src = r.get("src", "web")
            out.append(
                EvidenceItem(
                    eid=f"{src}:{r.get('rid', '')}",
                    claim_id=claim_id,
                    s=" ".join(re.sub(r"<[^>]+>", " ", str(text)).split()),
                    src=r.get("url") or src,
                    d=r.get("d"),
                    cred=r.get("cred") or cred_default.get(src, "med"),
                )
            )
        return out

    def _retrieve_for_query(self, claim_id: str, query: str, lim: int) -> List[EvidenceItem]:
        tools = ["kb_lookup"]
        if self.network_enabled:
            tools.append("search")
        if self._is_web_search_enabled():
            tools.append("web_search")

        for tool_id in tools:
            args: Dict[str, Any] = {"q": query, "lim": lim}
            if tool_id == "search":
                args["src"] = "wiki"
            retry = 0 if tool_id in {"search", "web_search", "kb_lookup"} else None
            out = self._run_tool_with_retry(tool_id, args, retries=retry)
            self.state.add_history(f"tool:{tool_id}", out.get("s", "error"), {"args": args, "e": out.get("e")})
            if out.get("s") != "ok":
                continue
            rows = extract_evidence_rows(out)
            if rows and self._query_overlap_ok(query, rows):
                return self._rows_to_evidence(rows, claim_id)
        return []

    def _dedupe_evidence(self, items: List[EvidenceItem]) -> List[EvidenceItem]:
        out: List[EvidenceItem] = []
        seen: Set[str] = set()
        for item in items:
            key = (item.s or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(item)
        return out

    def _fallback_select(self, claims: List[Dict[str, str]], ev_rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        return fallback_select(claims, ev_rows)

    def _select_evidence(self, claims: List[Dict[str, str]], ev_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, str]], str]:
        contract = "Return JSON: {sel:[{eid:str,for:str}]}. Select up to 5 from provided evidence only."
        llm_out = self._call_llm_json("evidence_selection", contract, {"claims": claims, "evidence": ev_rows}, max_tokens=220)
        valid_eids = {e.get("eid") for e in ev_rows}
        claim_ids = {c.get("id") for c in claims}
        default_cid = claims[0].get("id", "s1") if len(claims) == 1 else None
        eid_to_claim = {str(e.get("eid")): str(e.get("for")) for e in ev_rows if isinstance(e, dict)}
        snippet_to_eid = {" ".join(str(e.get("s", "")).lower().split())[:120]: str(e.get("eid")) for e in ev_rows if isinstance(e, dict)}

        if not isinstance(llm_out, dict):
            return self._fallback_select(claims, ev_rows), "fallback"

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
            return out[:5], "llm"
        self._llm_schema_mismatch("evidence_selection", llm_out)
        return self._fallback_select(claims, ev_rows), "fallback"

    def _fallback_nli(self, claims: List[Dict[str, str]], sel_rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        return fallback_nli(claims, sel_rows)

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
            return self._fallback_nli(claims, sel_rows), "fallback"

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
        self._llm_schema_mismatch("nli_verification", llm_out)
        return self._fallback_nli(claims, sel_rows), "fallback"

    def _fallback_decide(self, claims: List[Dict[str, str]], scores: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return fallback_decide(claims, scores)

    def _decide(self, claims: List[Dict[str, str]], scores: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str]:
        contract = "Return JSON: {ver:[{id:str,v:supported|refuted|mixed|insufficient,conf:low|med|high}]}"
        llm_out = self._call_llm_json("verdict_decision", contract, {"claims": claims, "scores": scores}, max_tokens=200)
        claim_ids = {c.get("id") for c in claims}
        default_cid = claims[0].get("id", "s1") if len(claims) == 1 else None
        if not isinstance(llm_out, dict):
            return self._fallback_decide(claims, scores), "fallback"

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
        self._llm_schema_mismatch("verdict_decision", llm_out)
        return self._fallback_decide(claims, scores), "fallback"

    def _fallback_output(self, claims: List[Dict[str, str]], verdicts: List[Dict[str, str]], selected: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        return fallback_output(claims, verdicts, selected)

    def _compose_output(self, claims: List[Dict[str, str]], verdicts: List[Dict[str, str]], selected: List[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], str]:
        contract = (
            "Return JSON: {out:[{id:str,ver:supported|refuted|mixed|insufficient,conf:low|med|high,r:str,cite:[str]}]}, "
            "with rationale <=220 chars."
        )
        llm_out = self._call_llm_json("response_output", contract, {"claims": claims, "verdicts": verdicts, "selected": selected}, max_tokens=260)
        claim_ids = {c.get("id") for c in claims}
        default_cid = claims[0].get("id", "s1") if len(claims) == 1 else None
        if not isinstance(llm_out, dict):
            return self._fallback_output(claims, verdicts, selected), "fallback"

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
        self._llm_schema_mismatch("response_output", llm_out)
        return self._fallback_output(claims, verdicts, selected), "fallback"

    def run(self, claim: str, step_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
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
                for p in plans:
                    cid = p.get("id", "s1")
                    lim = p.get("lim", 4)
                    for q in p.get("q", []):
                        n_queries += 1
                        collected.extend(self._retrieve_for_query(cid, q, lim))
                collected = self._dedupe_evidence(collected)
                if collected:
                    self.state.add_evidence(collected)
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
                self._set_default_verdicts()
                self._advance("error")
                continue

            if current == "SELECT_EVIDENCE":
                ev_in = [{"eid": e.eid, "for": e.claim_id, "s": e.s, "src": e.src, "d": e.d, "cred": e.cred} for e in self.state.evidence]
                if not ev_in:
                    self._emit_step(step_callback, step_no, current, "back", {"reason": "no_evidence"})
                    self._advance("back")
                    continue
                selected, via = self._select_evidence(self.state.claims, ev_in)
                if selected:
                    self.state.selected = selected
                    detail = {"via": via, "selected_n": len(selected)}
                    self.state.add_history("llm:evidence_selection", "ok", detail)
                    self._emit_step(step_callback, step_no, current, "ok", detail)
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
                self._set_default_verdicts()
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
                    self._set_default_verdicts()
                    self._emit_step(step_callback, step_no, current, "error", {"reason": "no_selected_rows"})
                    self._advance("error")
                    continue
                scores, via = self._nli_scores(self.state.claims, sel_rows)
                if scores:
                    self.state.scores = scores
                    detail = {"via": via, "scores_n": len(scores)}
                    self.state.add_history("llm:nli_verify", "ok", detail)
                    self._emit_step(step_callback, step_no, current, "ok", detail)
                    self._advance("ok")
                    continue
                self._set_default_verdicts()
                self._emit_step(step_callback, step_no, current, "error", {"reason": "nli_empty"})
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
                if not out_rows:
                    out_rows = self._fallback_output(self.state.claims, self.state.verdicts, self.state.selected)
                    via = "fallback"
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
        out_rows = self._fallback_output(claims, self.state.verdicts, self.state.selected)
        return {"s": "ok", "d": {"out": out_rows}, "e": None, "rb": "none"}


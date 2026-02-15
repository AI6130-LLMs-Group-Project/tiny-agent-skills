from __future__ import annotations

import importlib.util
import json
import os
import re
import urllib.request
from typing import Any, Dict, List, Optional, Set

from fsm import STATES, is_valid_state
from guardrail import basic_check, check_controller_action, check_tool_output, extract_evidence_rows, sanitize, trim_for_prompt
from skills import registry as skill_registry
from state import AgentState, EvidenceItem, load_env


_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "to", "of", "in", "on", "at",
    "for", "from", "by", "as", "that", "this", "it", "its", "and", "or", "with", "during", "into", "over",
    "under", "than", "then", "who", "what", "when", "where", "which",
}


class LlamaCppClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")

    def complete(self, system: str, user: str, temperature: float = 0.0, max_tokens: int = 900) -> str:
        url = self.endpoint + "/completion"
        payload = {"prompt": f"{system}\n\n{user}\n", "temperature": temperature, "n_predict": max_tokens}
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
        spec = importlib.util.spec_from_file_location(tool_id, meta["path"])
        mod = importlib.util.module_from_spec(spec)
        if spec and spec.loader:
            spec.loader.exec_module(mod)
        self._cache[tool_id] = mod
        return mod

    def run(self, tool_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        mod = self._load_module(tool_id)
        if not hasattr(mod, "run"):
            raise ValueError("tool has no run(): " + tool_id)
        return mod.run(args)


def _extract_json(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    dec = json.JSONDecoder()
    try:
        obj, _ = dec.raw_decode(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    for i, ch in enumerate(raw):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(raw[i:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    raise ValueError("no valid JSON object found")


def _terms(text: str) -> Set[str]:
    toks = set(re.findall(r"[a-z0-9]+", (text or "").lower()))
    return {t for t in toks if t and t not in _STOPWORDS}


class Orchestrator:
    def __init__(self, state: AgentState):
        load_env()
        endpoint = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:1025")
        self.n_retry = max(0, int(os.getenv("N_RETRY", "2")))
        self.max_steps = max(8, int(os.getenv("SOFT_FSM_MAX_STEPS", "24")))
        self.llm = LlamaCppClient(endpoint)
        self.tools = ToolExecutor()
        self.state = state
        self.controller_prompt = skill_registry.build_controller_prompt()

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

    def _tool_cards(self, current_state: str) -> List[Dict[str, Any]]:
        return [{"id": tid, "hint": skill_registry.TOOL_HINTS.get(tid, "")} for tid in skill_registry.STATE_TOOL_SCOPE.get(current_state, [])]

    def _call_controller(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "You MUST output STRICT JSON only. "
            "Return one JSON object with keys: s,d,e,rb. "
            "Allowed s: ok|error|retry."
        )
        user = self.controller_prompt + "\n\nINPUT:\n" + json.dumps(obs, ensure_ascii=True)
        last_err = "unknown"
        for attempt in range(self.n_retry + 1):
            suffix = "" if attempt == 0 else "\n\nIMPORTANT: previous output failed checks. Output one JSON object only."
            try:
                raw = self.llm.complete(system, user + suffix, temperature=0.0, max_tokens=900)
                data = sanitize(_extract_json(raw))
                ok, msg = basic_check(data)
                if not ok:
                    last_err = "BAD_SCHEMA: " + msg
                    continue
                ok2, msg2 = check_controller_action(data.get("d"))
                if not ok2:
                    last_err = "BAD_ACTION: " + msg2
                    continue
                return data
            except Exception as exc:
                last_err = str(exc)
        return {"s": "error", "d": None, "e": {"code": "BAD_CONTROLLER_OUTPUT", "msg": last_err}, "rb": "state"}

    def _dedupe_evidence(self) -> None:
        seen: Set[str] = set()
        out: List[EvidenceItem] = []
        for e in self.state.evidence:
            key = (e.s or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(e)
        self.state.evidence = out

    def _rows_to_evidence(self, rows: List[Dict[str, Any]], claim_id: str) -> List[EvidenceItem]:
        items: List[EvidenceItem] = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            text = r.get("snippet") or r.get("title") or ""
            if not text:
                continue
            text = re.sub(r"<[^>]+>", " ", str(text))
            text = " ".join(text.split())
            items.append(
                EvidenceItem(
                    eid=f"{r.get('src','web')}:{r.get('rid','')}",
                    claim_id=claim_id,
                    s=text,
                    src=r.get("url") or r.get("src", ""),
                    d=r.get("d"),
                    cred=r.get("cred", "med"),
                )
            )
        return items

    def _default_claims(self) -> List[Dict[str, Any]]:
        base = (self.state.norm_claim or self.state.claim or "").strip()
        if not base:
            base = "Unknown claim."
        return [{"id": "s1", "c": base}]

    def _safe_claims(self, claims: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not isinstance(claims, list):
            return out
        for idx, c in enumerate(claims, start=1):
            if not isinstance(c, dict):
                continue
            cid = c.get("id") or f"s{idx}"
            txt = c.get("c")
            if isinstance(txt, str) and txt.strip():
                out.append({"id": str(cid), "c": txt.strip()[:240]})
        return out

    def _safe_plans(self, plans: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not isinstance(plans, list):
            return out
        for p in plans:
            if not isinstance(p, dict):
                continue
            pid = p.get("id", "s1")
            q = p.get("q", [])
            lim = p.get("lim", 4)
            if not isinstance(q, list) or not q:
                continue
            qs = [str(x).strip() for x in q if isinstance(x, str) and x.strip()]
            if not qs:
                continue
            if not isinstance(lim, int) or lim < 1 or lim > 10:
                lim = 4
            out.append({"id": str(pid), "q": qs[:4], "lim": lim})
        return out

    def _safe_evidence_items(self, rows: Any) -> List[EvidenceItem]:
        out: List[EvidenceItem] = []
        if not isinstance(rows, list):
            return out
        for i, r in enumerate(rows, start=1):
            if not isinstance(r, dict):
                continue
            sent = r.get("s")
            cid = r.get("for") or r.get("claim_id")
            if not isinstance(sent, str) or not sent.strip():
                continue
            if not isinstance(cid, str) or not cid.strip():
                cid = self.state.claims[0].get("id", "s1") if self.state.claims else "s1"
            eid = r.get("eid") if isinstance(r.get("eid"), str) and r.get("eid") else f"llm:{self.state.rev}:{i}"
            src = r.get("src") if isinstance(r.get("src"), str) and r.get("src") else "llm"
            d = r.get("d") if isinstance(r.get("d"), str) else None
            cred = r.get("cred") if isinstance(r.get("cred"), str) else "med"
            out.append(EvidenceItem(eid=eid, claim_id=cid, s=sent.strip(), src=src, d=d, cred=cred))
        return out

    def _apply_write_patch(self, write: Dict[str, Any]) -> bool:
        changed = False
        if not isinstance(write, dict):
            return changed

        norm_claim = write.get("norm_claim")
        if isinstance(norm_claim, str) and norm_claim.strip():
            normalized = norm_claim.strip()[:240]
            if normalized != self.state.norm_claim:
                self.state.norm_claim = normalized
                changed = True

        claims = self._safe_claims(write.get("claims"))
        if claims and claims != self.state.claims:
            self.state.claims = claims
            changed = True

        plans = self._safe_plans(write.get("plans"))
        if plans and plans != self.state.plans:
            self.state.plans = plans
            changed = True

        evidence = self._safe_evidence_items(write.get("evidence"))
        if evidence:
            before = len(self.state.evidence)
            self.state.add_evidence(evidence)
            self._dedupe_evidence()
            if len(self.state.evidence) > before:
                changed = True

        selected = write.get("selected")
        if isinstance(selected, list):
            clean = []
            for s in selected:
                if not isinstance(s, dict):
                    continue
                eid = s.get("eid")
                cid = s.get("for")
                if isinstance(eid, str) and eid and isinstance(cid, str) and cid:
                    clean.append({"eid": eid, "for": cid})
            if clean != self.state.selected:
                self.state.selected = clean
                changed = True

        scores = write.get("scores")
        if isinstance(scores, list):
            clean_scores = [x for x in scores if isinstance(x, dict)]
            if clean_scores != self.state.scores:
                self.state.scores = clean_scores
                changed = True

        verdicts = write.get("verdicts")
        if isinstance(verdicts, list):
            clean_verdicts = [x for x in verdicts if isinstance(x, dict)]
            if clean_verdicts != self.state.verdicts:
                self.state.verdicts = clean_verdicts
                changed = True

        output = write.get("output")
        if isinstance(output, dict) and output != self.state.output:
            self.state.output = output
            changed = True

        return changed

    def _claim_id_from_args(self, args: Dict[str, Any]) -> str:
        cid = args.get("for") or args.get("claim_id")
        if isinstance(cid, str) and cid:
            return cid
        if self.state.claims:
            return self.state.claims[0].get("id", "s1")
        return "s1"

    def _apply_tool_output(self, args: Dict[str, Any], out: Dict[str, Any]) -> bool:
        if out.get("s") != "ok":
            return False
        rows = extract_evidence_rows(out)
        if not rows:
            return False
        claim_id = self._claim_id_from_args(args)
        self.state.add_evidence(self._rows_to_evidence(rows, claim_id))
        self._dedupe_evidence()
        return True

    def _default_output(self, reason: str) -> Dict[str, Any]:
        claims = self.state.claims or self._default_claims()
        return {
            "out": [
                {
                    "id": c.get("id", "s1"),
                    "ver": "insufficient",
                    "conf": "low",
                    "r": reason,
                    "cite": [],
                }
                for c in claims
            ]
        }

    def _controller_status_text(self, ctl: Dict[str, Any]) -> str:
        if ctl.get("s") == "error":
            err = ctl.get("e") or {}
            code = err.get("code", "ERR")
            msg = err.get("msg", "")
            return f"controller failed ({code}): {msg}"[:220]
        d = ctl.get("d") or {}
        analysis = str(d.get("analysis", "")).strip()
        action = str(d.get("next_action", "")).strip()
        if analysis and action:
            return (analysis + " | next: " + action)[:220]
        if analysis:
            return analysis[:220]
        if action:
            return ("next: " + action)[:220]
        return "controller step"

    def _tool_status_text(self, out: Dict[str, Any]) -> str:
        if out.get("s") == "ok":
            return "tool call succeeded"
        if out.get("s") == "retry":
            err = out.get("e") or {}
            return f"tool requested retry: {err.get('code', 'RETRY')}"
        err = out.get("e") or {}
        return f"tool failed: {err.get('code', 'UNKNOWN')}"

    def _make_default_plans(self) -> List[Dict[str, Any]]:
        claims = self.state.claims or self._default_claims()
        plans = []
        for c in claims:
            cid = c.get("id", "s1")
            txt = c.get("c", "")
            q = " ".join(txt.split()[:8]).strip() or txt
            plans.append({"id": cid, "q": [q], "lim": 4})
        return plans

    def _ensure_parse_progress(self) -> None:
        if not self.state.norm_claim:
            self.state.norm_claim = (self.state.claim or "").strip()
        if not self.state.claims:
            self.state.claims = [{"id": "s1", "c": self.state.norm_claim or (self.state.claim or "")}]
        if not self.state.plans:
            self.state.plans = self._make_default_plans()

    def _auto_select_from_evidence(self) -> List[Dict[str, Any]]:
        if not self.state.evidence:
            return []
        claim_map = {c.get("id", "s1"): c.get("c", "") for c in self.state.claims if isinstance(c, dict)}
        scored: List[Dict[str, Any]] = []
        for ev in self.state.evidence:
            claim_text = claim_map.get(ev.claim_id, "")
            score = len(_terms(claim_text).intersection(_terms(ev.s)))
            scored.append({"eid": ev.eid, "for": ev.claim_id, "score": score})
        scored.sort(key=lambda x: (-x["score"], x["eid"]))
        return [{"eid": s["eid"], "for": s["for"]} for s in scored[:5] if s.get("eid")]

    def _auto_scores_from_selected(self) -> List[Dict[str, Any]]:
        return [
            {"eid": s.get("eid", ""), "for": s.get("for", "s1"), "st": "neutral", "conf": "low"}
            for s in self.state.selected
            if isinstance(s, dict) and s.get("eid")
        ]

    def _auto_verdicts_from_scores(self) -> List[Dict[str, Any]]:
        ids = [c.get("id", "s1") for c in self.state.claims if isinstance(c, dict)] or ["s1"]
        out = []
        by_claim: Dict[str, List[Dict[str, Any]]] = {}
        for s in self.state.scores:
            if isinstance(s, dict):
                by_claim.setdefault(s.get("for", "s1"), []).append(s)
        for cid in ids:
            group = by_claim.get(cid, [])
            if any(x.get("st") == "refute" for x in group):
                out.append({"id": cid, "v": "refuted", "conf": "low"})
            elif any(x.get("st") == "support" for x in group):
                out.append({"id": cid, "v": "supported", "conf": "low"})
            else:
                out.append({"id": cid, "v": "insufficient", "conf": "low"})
        return out

    def _auto_output_from_verdicts(self) -> Dict[str, Any]:
        selected_map: Dict[str, List[str]] = {}
        for s in self.state.selected:
            if isinstance(s, dict) and s.get("for") and s.get("eid"):
                selected_map.setdefault(s["for"], []).append(s["eid"])
        out_rows = []
        for v in self.state.verdicts:
            if not isinstance(v, dict):
                continue
            cid = v.get("id", "s1")
            verdict = v.get("v", "insufficient")
            reason = "Evidence is insufficient for a reliable judgment."
            if verdict == "supported":
                reason = "Available evidence supports the claim."
            elif verdict == "refuted":
                reason = "Available evidence contradicts the claim."
            elif verdict == "mixed":
                reason = "Evidence is mixed and does not fully agree."
            out_rows.append({"id": cid, "ver": verdict, "conf": v.get("conf", "low"), "r": reason, "cite": selected_map.get(cid, [])[:2]})
        if not out_rows:
            out_rows = [{"id": "s1", "ver": "insufficient", "conf": "low", "r": "Evidence is insufficient for a reliable judgment.", "cite": []}]
        return {"out": out_rows}

    def _apply_stall_fallback(self, state_name: str) -> str:
        if state_name == "PARSE_CLAIM":
            self._ensure_parse_progress()
            self.state.add_history("guard:force_advance", "parse fallback generated plans; moving to RETRIEVAL", {})
            return "RETRIEVAL"
        if state_name == "RETRIEVAL":
            if self.state.evidence:
                self.state.add_history("guard:force_advance", "retrieval has evidence; moving to SELECT_EVIDENCE", {})
                return "SELECT_EVIDENCE"
            if self.state.plans:
                p = self.state.plans[0]
                q = (p.get("q") or [self.state.claim or ""])[0]
                auto_args = {"q": q, "lim": int(p.get("lim", 4)), "src": "wiki"}
                out = self._run_tool_with_retry("search", auto_args)
                self.state.add_history("tool:auto_search", self._tool_status_text(out), {"args": auto_args, "e": out.get("e")})
                self._apply_tool_output({"for": p.get("id", "s1")}, out)
                if self.state.evidence:
                    self.state.add_history("guard:force_advance", "auto retrieval produced evidence; moving to SELECT_EVIDENCE", {})
                    return "SELECT_EVIDENCE"
            return "RETRIEVAL"
        if state_name == "SELECT_EVIDENCE":
            if not self.state.selected and self.state.evidence:
                self.state.selected = self._auto_select_from_evidence()
            if self.state.selected:
                self.state.add_history("guard:force_advance", "selected evidence via fallback; moving to NLI_VERIFY", {})
                return "NLI_VERIFY"
            return "RETRIEVAL"
        if state_name == "NLI_VERIFY":
            if not self.state.scores and self.state.selected:
                self.state.scores = self._auto_scores_from_selected()
            if self.state.scores:
                self.state.add_history("guard:force_advance", "generated fallback scores; moving to DECIDE", {})
                return "DECIDE"
            return "RETRIEVAL"
        if state_name == "DECIDE":
            if not self.state.verdicts:
                self.state.verdicts = self._auto_verdicts_from_scores()
            self.state.add_history("guard:force_advance", "generated fallback verdicts; moving to OUTPUT", {})
            return "OUTPUT"
        if state_name == "OUTPUT":
            if not self.state.output:
                self.state.output = self._auto_output_from_verdicts()
            return "OUTPUT"
        return state_name

    def _default_retrieval_query(self, claim_id: Optional[str] = None) -> str:
        if claim_id and self.state.plans:
            for plan in self.state.plans:
                if not isinstance(plan, dict) or plan.get("id") != claim_id:
                    continue
                q = plan.get("q")
                if isinstance(q, list):
                    for item in q:
                        if isinstance(item, str) and item.strip():
                            return item.strip()

        for plan in self.state.plans:
            if not isinstance(plan, dict):
                continue
            q = plan.get("q")
            if isinstance(q, list):
                for item in q:
                    if isinstance(item, str) and item.strip():
                        return item.strip()

        if isinstance(self.state.norm_claim, str) and self.state.norm_claim.strip():
            return self.state.norm_claim.strip()
        if isinstance(self.state.claim, str) and self.state.claim.strip():
            return self.state.claim.strip()
        if self.state.claims:
            first = self.state.claims[0]
            if isinstance(first, dict):
                c = first.get("c")
                if isinstance(c, str) and c.strip():
                    return c.strip()
        return ""

    def _default_retrieval_limit(self, claim_id: Optional[str], tool_id: str) -> int:
        hard_cap = 20 if tool_id == "kb_lookup" else 10
        fallback = 4

        if claim_id and self.state.plans:
            for plan in self.state.plans:
                if isinstance(plan, dict) and plan.get("id") == claim_id and isinstance(plan.get("lim"), int):
                    lim = plan.get("lim")
                    if 1 <= lim <= hard_cap:
                        return lim

        if self.state.plans:
            first = self.state.plans[0]
            if isinstance(first, dict) and isinstance(first.get("lim"), int):
                lim = first.get("lim")
                if 1 <= lim <= hard_cap:
                    return lim

        return min(fallback, hard_cap)

    def _normalize_tool_call(self, call: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(call, dict):
            return None

        tool = call.get("tool")
        if not isinstance(tool, str):
            return None
        tool_id = tool.strip()
        if not tool_id or tool_id.lower() in {"none", "null", "no_tool"}:
            return None

        args = call.get("args") if isinstance(call.get("args"), dict) else {}
        args = dict(args)

        claim_id = None
        for k in ("for", "claim_id"):
            v = args.get(k)
            if isinstance(v, str) and v.strip():
                claim_id = v.strip()
                break

        if tool_id in {"search", "kb_lookup", "web_search"}:
            q = args.get("q")
            if not isinstance(q, str) or not q.strip():
                q = self._default_retrieval_query(claim_id)
            if isinstance(q, str) and q.strip():
                args["q"] = q.strip()

            lim = args.get("lim")
            cap = 20 if tool_id == "kb_lookup" else 10
            if not isinstance(lim, int) or not (1 <= lim <= cap):
                args["lim"] = self._default_retrieval_limit(claim_id, tool_id)

        if tool_id == "search":
            if args.get("src") == "kb":
                args["src"] = "wiki"
            if args.get("src") not in {"wiki", "web", "news"}:
                args["src"] = "wiki"

        return {"tool": tool_id, "args": args}

    def _resolve_next_state(self, current_state: str, proposed_next: Any) -> str:
        next_state = proposed_next.strip() if isinstance(proposed_next, str) else ""
        if not is_valid_state(next_state):
            next_state = current_state

        if current_state == "PARSE_CLAIM":
            self._ensure_parse_progress()
            return "RETRIEVAL"

        if current_state == "RETRIEVAL":
            if next_state == "SELECT_EVIDENCE" and not self.state.evidence:
                return "RETRIEVAL"
            return next_state if next_state in {"RETRIEVAL", "SELECT_EVIDENCE", "OUTPUT"} else "RETRIEVAL"

        if current_state == "SELECT_EVIDENCE":
            if next_state == "NLI_VERIFY" and not self.state.selected:
                return "SELECT_EVIDENCE"
            return next_state if next_state in {"SELECT_EVIDENCE", "NLI_VERIFY", "RETRIEVAL", "OUTPUT"} else "SELECT_EVIDENCE"

        if current_state == "NLI_VERIFY":
            if next_state == "DECIDE" and not self.state.scores:
                return "NLI_VERIFY"
            return next_state if next_state in {"NLI_VERIFY", "DECIDE", "RETRIEVAL", "OUTPUT"} else "NLI_VERIFY"

        if current_state == "DECIDE":
            if next_state == "OUTPUT" and not self.state.verdicts:
                return "DECIDE"
            return next_state if next_state in {"DECIDE", "OUTPUT", "RETRIEVAL"} else "DECIDE"

        if current_state == "OUTPUT":
            return "OUTPUT"

        return current_state

    def run(self, claim: str) -> Dict[str, Any]:
        self.state.claim = claim
        self.state.claims = [{"id": "s1", "c": claim}]
        last_tool: Optional[Dict[str, Any]] = None
        stall_counts: Dict[str, int] = {}

        for _ in range(self.max_steps):
            current_state = self.state.fsm
            obs = {
                "states": STATES,
                "current_state": current_state,
                "tools_in_scope": self._tool_cards(current_state),
                "memory": trim_for_prompt(self.state.snapshot()),
                "last_tool": last_tool,
            }
            ctl = self._call_controller(obs)
            self.state.add_history("controller", self._controller_status_text(ctl), ctl)

            if ctl.get("s") == "error":
                self.state.tick("OUTPUT")
                self.state.output = self._default_output("Controller output invalid after retries.")
                return {"s": "ok", "d": self.state.output, "e": None, "rb": "none"}

            d = ctl.get("d") or {}
            wrote = False
            called = False

            if ctl.get("s") != "retry":
                wrote = self._apply_write_patch(d.get("write") or {})

                raw_call = d.get("call") if isinstance(d.get("call"), dict) else None
                norm_call = self._normalize_tool_call(raw_call) if raw_call else None
                if raw_call and not norm_call:
                    self.state.add_history("guard:drop_call", "ignored invalid/no-op tool call", {"call": raw_call})

                if norm_call:
                    tool_id = norm_call["tool"]
                    args = norm_call["args"]
                    in_scope = tool_id in skill_registry.STATE_TOOL_SCOPE.get(current_state, [])
                    if not in_scope:
                        self.state.add_history(
                            "guard:drop_call",
                            f"ignored out-of-scope tool call `{tool_id}` in {current_state}",
                            {"args": args},
                        )
                    else:
                        out = self._run_tool_with_retry(tool_id, args)
                        self.state.add_history(f"tool:{tool_id}", self._tool_status_text(out), {"args": args, "e": out.get("e")})
                        tool_changed = self._apply_tool_output(args, out)
                        called = called or tool_changed
                        last_tool = {
                            "tool": tool_id,
                            "status": self._tool_status_text(out),
                            "data": out.get("d"),
                            "error": out.get("e"),
                        }

            nxt = self._resolve_next_state(current_state, d.get("next", current_state))

            progressed = wrote or called or (nxt != current_state)
            if progressed:
                stall_counts[current_state] = 0
            else:
                stall_counts[current_state] = stall_counts.get(current_state, 0) + 1
                if stall_counts[current_state] >= 2:
                    nxt = self._apply_stall_fallback(current_state)
                    stall_counts[current_state] = 0

            self.state.tick(nxt)

            if self.state.fsm == "RETRIEVAL" and not self.state.plans and self.state.claims:
                self.state.plans = self._make_default_plans()

            if self.state.fsm == "OUTPUT" and self.state.output:
                return {"s": "ok", "d": self.state.output, "e": None, "rb": "none"}
            if d.get("done") and self.state.output:
                return {"s": "ok", "d": self.state.output, "e": None, "rb": "none"}

        self.state.tick("OUTPUT")
        if not self.state.output:
            self.state.output = self._default_output("Max steps reached.")
        return {"s": "ok", "d": self.state.output, "e": None, "rb": "none"}

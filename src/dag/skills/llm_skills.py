"""
Fact-checking DAG skills: query_gen, evidence_extract, verify call local LLM; retrieve is a placeholder (replace with real retrieval later).
"""

from __future__ import annotations

from typing import Any

from dag.llm_client import chat
from dag.pipeline import Skill


def _get_base_url() -> str:
    return __import__("os").environ.get("LLM_BASE_URL", "http://localhost:1025/v1")


# -----------------------------------------------------------------------------
# query_gen: claim -> search query (1 LLM call)
# -----------------------------------------------------------------------------


class _QueryGenSkill:
    """
    Input:  context with "claim" (str).
    Output: context updates {"queries": [str], "last_step": "query_gen"}.
    """

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        claim = context.get("claim", "")
        base_url = _get_base_url()
        text = chat(
            [
                {"role": "system", "content": "You output a single short search query to find evidence for the claim. One line only, no explanation."},
                {"role": "user", "content": f"Claim: {claim}\nSearch query:"},
            ],
            base_url=base_url,
        )
        query = text.split("\n")[0].strip() or claim
        return {"queries": [query], "last_step": "query_gen"}


# -----------------------------------------------------------------------------
# evidence_extract: claim + snippets -> one evidence sentence or NONE (1 LLM call)
# -----------------------------------------------------------------------------

EVIDENCE_EXTRACT_SYSTEM = """Given a claim and retrieved snippets, output either:
1) The single sentence that best supports or refutes the claim (copy or shorten from snippets), OR
2) NONE if no snippet is relevant to the claim.

Reply with only the evidence sentence or the word NONE. No explanation."""


class _EvidenceExtractSkill:
    """
    Input:  context with "claim", "snippets" (list of str).
    Output: {"evidence": [{"text": str, "score": float}] or [], "evidence_count": int, "last_step": "evidence_extract"}.
    """

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        claim = context.get("claim", "")
        snippets = context.get("snippets", [])
        if not snippets:
            return {"evidence": [], "evidence_count": 0, "last_step": "evidence_extract"}
        snippets_text = "\n".join(s[:400] for s in snippets if isinstance(s, str)) or str(snippets)[:800]
        base_url = _get_base_url()
        text = chat(
            [
                {"role": "system", "content": EVIDENCE_EXTRACT_SYSTEM},
                {"role": "user", "content": f"Claim: {claim}\n\nSnippets:\n{snippets_text}\n\nEvidence sentence or NONE:"},
            ],
            base_url=base_url,
        )
        text = text.strip()
        if not text or text.upper() == "NONE" or text.upper().startswith("NONE "):
            return {"evidence": [], "evidence_count": 0, "last_step": "evidence_extract"}
        first_line = text.split("\n")[0].strip()
        if first_line.upper().startswith("NONE"):
            return {"evidence": [], "evidence_count": 0, "last_step": "evidence_extract"}
        return {
            "evidence": [{"text": first_line, "score": 0.9}],
            "evidence_count": 1,
            "last_step": "evidence_extract",
        }


# -----------------------------------------------------------------------------
# verify: claim + evidence -> Support | Refute | NEI (1 LLM call)
# -----------------------------------------------------------------------------

VERIFY_SYSTEM = """You are a fact-checker. Reply with exactly one word: Support, Refute, or NEI.

Definitions:
- Support: The evidence clearly states something that backs the claim.
- Refute: The evidence is about the same fact as the claim but states the OPPOSITE or a conflicting fact (e.g. claim "X is Y", evidence says "X is not Y"). If the evidence clearly contradicts the claim, say Refute — do not treat contradicting evidence as "irrelevant" (NEI).
- NEI: The evidence does not address the claim (different topic, or no real information). Use NEI when evidence is truly off-topic or silent on the claim, not when it contradicts.

Important: Evidence that contradicts the claim is still "relevant" — it speaks to the claim and says the opposite, so answer Refute. Only use NEI when the evidence does not speak to the claim at all (missing, different subject, or too vague to tell). When in doubt: if evidence and claim are about the same thing but conflict -> Refute; if evidence is about something else or says nothing about the claim -> NEI."""

VERIFY_USER_TEMPLATE = """Claim: {claim}

Evidence:
{evidence}

If the evidence is about the same fact as the claim but says the opposite, answer Refute (do not call it NEI). If the evidence does not address the claim at all, answer NEI.
One word: Support, Refute, or NEI?"""


class _VerifySkill:
    """
    Input:  context with "claim", "evidence" (list of dicts with "text").
    Output: {"label": "Support"|"Refute"|"NEI", "last_step": "verify"}. If evidence is empty, returns label "NEI" without calling LLM.
    """

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        claim = context.get("claim", "")
        evidence = context.get("evidence", [])
        if not evidence:
            return {"label": "NEI", "last_step": "verify"}
        evidence_text = "\n".join(
            e.get("text", str(e))[:500] for e in evidence[:5]
        )
        base_url = _get_base_url()
        text = chat(
            [
                {"role": "system", "content": VERIFY_SYSTEM},
                {"role": "user", "content": VERIFY_USER_TEMPLATE.format(claim=claim, evidence=evidence_text)},
            ],
            base_url=base_url,
        )
        label = "NEI"
        for w in ("Support", "Refute", "NEI"):
            if w.lower() in text.lower():
                label = w
                break
        return {"label": label, "last_step": "verify"}


# -----------------------------------------------------------------------------
# retrieve: placeholder (no real API); output -> snippets for downstream
# -----------------------------------------------------------------------------


class _RetrieveSkill:
    """
    Input:  context with "queries" (list of str).
    Output: {"snippets": [str, ...], "last_step": "retrieve"}. Placeholder: one fake snippet per query; replace with real retrieval API.
    """

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        queries = context.get("queries", [])
        snippets = [f"[snippet for: {q}]" for q in queries]
        return {"snippets": snippets, "last_step": "retrieve"}


# -----------------------------------------------------------------------------
# output: format final string
# -----------------------------------------------------------------------------


class _OutputSkill:
    """
    Input:  context with "claim", "label".
    Output: {"output": "Claim: ...\nVerification: ...", "last_step": "output"}.
    """

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        claim = context.get("claim", "")
        label = context.get("label", "NEI")
        return {"output": f"Claim: {claim}\nVerification: {label}", "last_step": "output"}


def fact_check_skill_registry() -> dict[str, Skill]:
    """
    Input:  none.
    Output: registry dict skill_id -> Skill for the fact-check DAG (query_gen, retrieve, evidence_extract, verify, output).
    """
    return {
        "query_gen": _QueryGenSkill(),
        "retrieve": _RetrieveSkill(),
        "evidence_extract": _EvidenceExtractSkill(),
        "verify": _VerifySkill(),
        "output": _OutputSkill(),
    }

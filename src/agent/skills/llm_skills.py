"""
事实核查 pipeline 的 skills：全部接本地 LLM 接口（query_gen、evidence_extract、verify）。
retrieve 为占位实现（无真实检索 API 时保证 pipeline 可跑），后续可替换为真实检索。
"""

from __future__ import annotations

from typing import Any

from agent.llm_client import chat
from agent.pipeline import Skill


def _get_base_url() -> str:
    import os
    return os.environ.get("LLM_BASE_URL", "http://localhost:1025/v1")


class _QueryGenSkill:
    """从 claim 生成检索 query，调本地 LLM。"""

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


# ----- evidence_extract：从 snippets 里抽一句相关证据，或判无相关 -----
EVIDENCE_EXTRACT_SYSTEM = """Given a claim and retrieved snippets, output either:
1) The single sentence that best supports or refutes the claim (copy or shorten from snippets), OR
2) NONE if no snippet is relevant to the claim.

Reply with only the evidence sentence or the word NONE. No explanation."""


class _EvidenceExtractSkill:
    """用 LLM 从 snippets 中抽取与 claim 最相关的一句，或判 NONE。"""

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


# ----- verify：三分类 + 明确 few-shot，强调 Refute -----
VERIFY_SYSTEM = """You are a fact-checker. Reply with exactly one word: Support, Refute, or NEI.

- Support: The evidence clearly backs the claim.
- Refute: The evidence says the OPPOSITE of the claim or clearly contradicts it. You MUST say Refute when you see this.
- NEI: No relevant evidence, or evidence does not clearly support or refute.

Important: Do not skip Refute. If the evidence contradicts the claim, your answer must be Refute."""

VERIFY_FEWSHOT = """
Example 1 - Support:
Claim: The film Soul Food was released by Fox 2000 Pictures.
Evidence: Fox 2000 Pictures released Soul Food in 1997.
Answer: Support

Example 2 - Refute (evidence contradicts claim):
Claim: Telemundo is an English-language network.
Evidence: Telemundo is a Spanish-language television network.
Answer: Refute

Example 3 - Refute (evidence contradicts claim):
Claim: Sean Penn is only a stage actor.
Evidence: Sean Penn is known for his film roles and won Academy Awards for movies.
Answer: Refute

Example 4 - NEI:
Claim: Anne Rice was born in New Jersey.
Evidence: (no relevant evidence)
Answer: NEI
"""

VERIFY_USER_TEMPLATE = """Claim: {claim}

Evidence:
{evidence}
""" + VERIFY_FEWSHOT + """
Now answer for the claim above. If the evidence contradicts the claim, say Refute. One word only: Support, Refute, or NEI?"""


class _VerifySkill:
    """根据 claim + evidence 做 Support/Refute/NEI，调本地 LLM。"""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        claim = context.get("claim", "")
        evidence = context.get("evidence", [])
        if not evidence:
            return {"label": "NEI", "last_step": "verify"}
        evidence_text = "\n".join(
            e.get("text", str(e))[:500] for e in evidence[:5]
        )
        base_url = _get_base_url()
        user_content = VERIFY_USER_TEMPLATE.format(
            claim=claim, evidence=evidence_text
        )
        text = chat(
            [
                {"role": "system", "content": VERIFY_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            base_url=base_url,
        )
        label = "NEI"
        for w in ("Support", "Refute", "NEI"):
            if w.lower() in text.lower():
                label = w
                break
        return {"label": label, "last_step": "verify"}


class _RetrieveSkill:
    """检索：占位实现，返回与 query 对应的占位 snippet。TODO: 接真实检索 API/向量库。"""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        queries = context.get("queries", [])
        snippets = [f"[snippet for: {q}]" for q in queries]
        return {"snippets": snippets, "last_step": "retrieve"}


class _OutputSkill:
    """格式化最终输出。"""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        claim = context.get("claim", "")
        label = context.get("label", "NEI")
        return {"output": f"Claim: {claim}\nVerification: {label}", "last_step": "output"}


def fact_check_skill_registry() -> dict[str, Skill]:
    """事实核查 pipeline 的 skill 注册表（全部走本地 LLM，retrieve 为占位）。"""
    return {
        "query_gen": _QueryGenSkill(),
        "retrieve": _RetrieveSkill(),
        "evidence_extract": _EvidenceExtractSkill(),
        "verify": _VerifySkill(),
        "output": _OutputSkill(),
    }

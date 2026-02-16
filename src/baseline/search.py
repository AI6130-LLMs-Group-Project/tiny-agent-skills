"""
Simple Wikipedia search tool for baseline FEVER runs.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

USER_AGENT = "tiny-agent-skills-baseline/1.0 (+local)"


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def search_wiki(query: str, limit: int = 3) -> list[dict[str, Any]]:
    q = (query or "").strip()
    lim = max(1, min(int(limit), 10))
    if not q:
        return []

    params = {
        "action": "query",
        "list": "search",
        "srsearch": q,
        "format": "json",
        "utf8": 1,
        "srlimit": lim,
    }
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    results: list[dict[str, Any]] = []
    for idx, hit in enumerate(payload.get("query", {}).get("search", []), start=1):
        title = hit.get("title", "")
        page_url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        results.append(
            {
                "rank": idx,
                "title": title,
                "snippet": _clean(hit.get("snippet", "")),
                "url": page_url,
            }
        )
    return results


def run(args: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(args, dict):
        return {"ok": False, "error": "args must be an object", "results": []}
    query = args.get("query", "")
    limit = args.get("limit", 3)
    try:
        results = search_wiki(str(query), int(limit))
    except Exception as exc:
        return {"ok": False, "error": str(exc), "results": []}
    return {"ok": True, "error": None, "results": results}


if __name__ == "__main__":
    print(json.dumps(run({"query": "Apollo 11", "limit": 3}), ensure_ascii=True, indent=2))

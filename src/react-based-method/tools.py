import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import time

from tool_registry import ToolRegistry, tool


registry = ToolRegistry()


class _State:
    page_text = ""
    lookup_index = 0


STATE = _State()


def _http_json(url: str, timeout: int = 30, headers: dict | None = None) -> dict:
    base_headers = {
        "User-Agent": "Tiny_Agent_Skills_Eval/1.0 (research purpose; contact@example.com)"
    }
    if headers:
        base_headers.update(headers)
    
    req = Request(url, method="GET")
    for k, v in base_headers.items():
        req.add_header(k, v)
        
    for attempt in range(5):
        try:
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == 4:
                raise e
            time.sleep(2 * (2 ** attempt))  # Exponential backoff: 2, 4, 8, 16s



def _split_sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def reset():
    STATE.page_text = ""
    STATE.lookup_index = 0


def get_tool_registry() -> ToolRegistry:
    return registry


registry.reset = reset


@tool(
    registry,
    name="wiki_search",
    description="Search Wikipedia and return the first 5 sentences of the best match.",
    parameters={
        "type": "object",
        "properties": {"entity": {"type": "string"}},
        "required": ["entity"],
    },
)
def wiki_search(entity: str) -> str:
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": entity,
        "format": "json",
    }
    headers = {"User-Agent": "Tiny_Agent_Skills/0.1 (local)"}
    sdata = _http_json(
        "https://en.wikipedia.org/w/api.php?" + urlencode(search_params),
        timeout=30,
        headers=headers,
    )
    results = sdata.get("query", {}).get("search", [])
    if not results:
        STATE.page_text = ""
        STATE.lookup_index = 0
        return "Similar: []"

    title = results[0]["title"]
    extract_params = {
        "action": "query",
        "prop": "extracts",
        "titles": title,
        "explaintext": 1,
        "exsentences": 5,
        "format": "json",
    }
    edata = _http_json(
        "https://en.wikipedia.org/w/api.php?" + urlencode(extract_params),
        timeout=30,
        headers=headers,
    )
    pages = edata.get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    intro = page.get("extract", "").strip()

    full_params = {
        "action": "query",
        "prop": "extracts",
        "titles": title,
        "explaintext": 1,
        "format": "json",
    }
    fdata = _http_json(
        "https://en.wikipedia.org/w/api.php?" + urlencode(full_params),
        timeout=30,
        headers=headers,
    )
    fpages = fdata.get("query", {}).get("pages", {})
    fpage = next(iter(fpages.values()))
    STATE.page_text = fpage.get("extract", "").strip()
    STATE.lookup_index = 0

    return intro if intro else "Similar: []"


@tool(
    registry,
    name="wiki_lookup",
    description="Lookup the next sentence containing a string from the current Wikipedia page.",
    parameters={
        "type": "object",
        "properties": {"keyword": {"type": "string"}},
        "required": ["keyword"],
    },
)
def wiki_lookup(keyword: str) -> str:
    if not STATE.page_text:
        return "No match found"
    sentences = _split_sentences(STATE.page_text)
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    for i in range(STATE.lookup_index, len(sentences)):
        if pattern.search(sentences[i]):
            STATE.lookup_index = i + 1
            return sentences[i]
    return "No match found"

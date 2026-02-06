import json
import re
from typing import Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import time


class WikiEnv:
    def __init__(self):
        self.page_text = ""
        self.lookup_index = 0

    def _http_json(self, url: str, timeout: int = 30, headers: Optional[dict] = None) -> dict:
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
                time.sleep(2 * (2 ** attempt))

    def _wiki_search(self, entity: str) -> Tuple[str, Optional[str], Optional[str]]:
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": entity,
            "format": "json",
        }
        headers = {"User-Agent": "Tiny_Agent_Skills/0.1 (local)"}
        sdata = self._http_json(
            "https://en.wikipedia.org/w/api.php?" + urlencode(search_params),
            timeout=30,
            headers=headers,
        )
        results = sdata.get("query", {}).get("search", [])
        if not results:
            return "Similar: []", None, None

        title = results[0]["title"]
        extract_params = {
            "action": "query",
            "prop": "extracts",
            "titles": title,
            "explaintext": 1,
            "exsentences": 5,
            "format": "json",
        }
        edata = self._http_json(
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
        fdata = self._http_json(
            "https://en.wikipedia.org/w/api.php?" + urlencode(full_params),
            timeout=30,
            headers=headers,
        )
        fpages = fdata.get("query", {}).get("pages", {})
        fpage = next(iter(fpages.values()))
        full_text = fpage.get("extract", "").strip()

        observation = intro if intro else "Similar: []"
        return observation, title, full_text

    def _split_sentences(self, text: str):
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _wiki_lookup(self, keyword: str) -> str:
        if not self.page_text:
            return "No match found"
        sentences = self._split_sentences(self.page_text)
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        for i in range(self.lookup_index, len(sentences)):
            if pattern.search(sentences[i]):
                self.lookup_index = i + 1
                return sentences[i]
        return "No match found"

    def reset(self):
        self.page_text = ""
        self.lookup_index = 0

    def step(self, action: str) -> str:
        action = action.strip()
        m = re.match(r"(?i)^(search|lookup|finish)\[(.*)\]\s*$", action)
        if not m:
            raise ValueError(f"Invalid action format: {action}")
        action_type = m.group(1).lower()
        action_arg = m.group(2).strip()

        if action_type == "search":
            observation, _title, full_text = self._wiki_search(action_arg)
            self.page_text = full_text or ""
            self.lookup_index = 0
            return observation
        if action_type == "lookup":
            return self._wiki_lookup(action_arg)
        if action_type == "finish":
            return ""
        raise ValueError(f"Unsupported action: {action_type}")

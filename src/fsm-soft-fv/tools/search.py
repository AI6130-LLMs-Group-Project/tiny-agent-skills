import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from html import unescape

_VALID_SRC = {"wiki", "web", "news"}
_USER_AGENT = "tiny-agent-skills/1.0 (+https://local)"


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}}


def _ok(results):
    return {"s": "ok", "d": {"results": results}, "e": None}


def _load_runtime_env():
    if getattr(_load_runtime_env, "_loaded", False):
        return
    root = Path(__file__).resolve().parents[3]
    env_path = root / ".env"
    if env_path.is_file():
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k and k not in os.environ:
                    os.environ[k] = v
    _load_runtime_env._loaded = True


def _clean(text):
    if text is None:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def _http_timeout():
    try:
        val = int(os.getenv("RETRIEVAL_HTTP_TIMEOUT", "4"))
    except Exception:
        val = 4
    if val < 1:
        return 1
    if val > 15:
        return 15
    return val


def _wiki_search(q, lim):
    params = {
        "action": "query",
        "list": "search",
        "srsearch": q,
        "format": "json",
        "utf8": 1,
        "srlimit": lim,
    }
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_http_timeout()) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    items = []
    for i, hit in enumerate(data.get("query", {}).get("search", []), start=1):
        title = hit.get("title", "")
        snippet = _clean(hit.get("snippet", ""))
        page_url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        items.append(
            {
                "rid": f"r{i}",
                "title": title,
                "snippet": snippet,
                "url": page_url,
                "src": "wiki",
                "d": None,
            }
        )
    return items


def _duckduckgo_search(q, lim, src):
    params = {
        "q": q,
        "format": "json",
        "no_redirect": 1,
        "no_html": 1,
    }
    url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_http_timeout()) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    items = []
    pool = []
    pool.extend(data.get("Results", []))
    for t in data.get("RelatedTopics", []):
        if isinstance(t, dict) and "Topics" in t:
            pool.extend(t.get("Topics", []))
        else:
            pool.append(t)
    for item in pool:
        if not isinstance(item, dict):
            continue
        text = item.get("Text", "")
        url_item = item.get("FirstURL", "")
        if not text or not url_item:
            continue
        title = text.split(" - ", 1)[0]
        items.append(
            {
                "rid": f"r{len(items) + 1}",
                "title": _clean(title),
                "snippet": _clean(text),
                "url": url_item,
                "src": src,
                "d": None,
            }
        )
        if len(items) >= lim:
            break
    return items


def run(args):
    """
    Args schema:
      {"q": str, "lim": int, "src": "wiki|web|news"}

    Returns:
      {"s": "ok|error", "d": {"results": [..]}, "e": {..}|None}
    """
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be an object")
    _load_runtime_env()
    q = (args.get("q") or "").strip()
    lim = args.get("lim")
    src = args.get("src")
    if not q:
        return _err("EMPTY_QUERY", "q is required")
    if not isinstance(lim, int) or lim < 1 or lim > 10:
        return _err("BAD_LIMIT", "lim must be 1..10")
    if src not in _VALID_SRC:
        return _err("BAD_SRC", "src must be wiki|web|news")

    try:
        if src == "wiki":
            results = _wiki_search(q, lim)
        else:
            results = _duckduckgo_search(q, lim, src)
        return _ok(results)
    except Exception as exc:
        return _err("FETCH_FAIL", str(exc))

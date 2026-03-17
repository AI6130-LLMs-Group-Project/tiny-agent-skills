### This tool performs a web search using SerpAPI or Tavily API (better within free tier)

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path


_VALID_PROVIDERS = {"serpapi", "tavily"}
_USER_AGENT = "tiny-agent-skills/1.0 (+https://local)"


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


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}}


def _ok(results):
    return {"s": "ok", "d": {"results": results}, "e": None}


def _append_evidence(results):
    kb_path = os.getenv("KB_PATH")
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if not kb_path:
        kb_path = os.path.join(root, "runtime", "evidence.jsonl")
    if not os.path.isabs(kb_path):
        kb_path = os.path.abspath(os.path.join(root, kb_path))
    os.makedirs(os.path.dirname(kb_path), exist_ok=True)
    now = time.strftime("%Y-%m-%d")
    with open(kb_path, "a", encoding="utf-8") as f:
        for r in results:
            text = r.get("snippet") or r.get("title") or ""
            item = {
                "id": f"web:{r.get('rid','')}",
                "text": text,
                "src": r.get("url") or r.get("src", ""),
                "d": r.get("d") or now,
                "cred": "med",
            }
            f.write(json.dumps(item, ensure_ascii=True) + "\n")


def _serpapi_search(q, lim, key):
    params = {"q": q, "api_key": key, "num": lim}
    url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    items = []
    for i, v in enumerate(data.get("organic_results", []), start=1):
        items.append(
            {
                "rid": f"r{i}",
                "title": v.get("title", ""),
                "snippet": v.get("snippet", ""),
                "url": v.get("link", ""),
                "src": "web",
                "d": None,
            }
        )
    return items


def _tavily_search(q, lim, key):
    url = "https://api.tavily.com/search"
    payload = json.dumps({"query": q, "max_results": lim}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    items = []
    for i, v in enumerate(data.get("results", []), start=1):
        items.append(
            {
                "rid": f"r{i}",
                "title": v.get("title", ""),
                "snippet": v.get("content", ""),
                "url": v.get("url", ""),
                "src": "web",
                "d": None,
            }
        )
    return items


def _pick_provider(args):
    provider = args.get("provider")
    if provider:
        return provider
    env_provider = os.getenv("WEB_SEARCH_PROVIDER")
    if env_provider:
        return env_provider
    if args.get("serpapi_key"):
        return "serpapi"
    if args.get("tavily_key"):
        return "tavily"
    return None


def run(args):
    """
    Args schema:
        {"q": str, "lim": int, "provider": "serpapi|tavily"|null,
        "serpapi_key": str|null, "tavily_key": str|null}

    Returns:
        {"s": "ok|error", "d": {"results": [..]}, "e": {..}|None}
    """
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be an object")
    _load_runtime_env()
    q = (args.get("q") or "").strip()
    lim = args.get("lim")
    if not q:
        return _err("EMPTY_QUERY", "q is required")
    if not isinstance(lim, int) or lim < 1 or lim > 10:
        return _err("BAD_LIMIT", "lim must be 1..10")

    provider = _pick_provider(args)
    if provider not in _VALID_PROVIDERS:
        return _err("NO_PROVIDER", "set provider or API key")

    try:
        if provider == "serpapi":
            key = args.get("serpapi_key") or os.getenv("SERPAPI_KEY")
            if not key:
                return _err("NO_KEY", "serpapi_key is required")
            results = _serpapi_search(q, lim, key)
        else:
            key = args.get("tavily_key") or os.getenv("TAVILY_API_KEY")
            if not key:
                return _err("NO_KEY", "tavily_key is required")
            results = _tavily_search(q, lim, key)
        out = _ok(results)
        _append_evidence(results)
        return out
    except Exception as exc:
        return _err("FETCH_FAIL", str(exc))


# Quick test lah
if __name__ == "__main__":
    sample = {"q": "Apollo 11 1969", "lim": 3}
    print(json.dumps(run(sample), ensure_ascii=True))

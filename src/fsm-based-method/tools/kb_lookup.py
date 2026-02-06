### Might be useless, but my engineering brain says to keep it!

import json
import os


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}}


def _ok(items):
    return {"s": "ok", "d": {"items": items}, "e": None}


def _load_kb(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _load_runtime_env():
    if getattr(_load_runtime_env, "_loaded", False):
        return
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(root, ".env")
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
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


def _score(text, terms):
    t = text.lower()
    return sum(1 for term in terms if term in t)


def run(args):
    """
    Args schema:
        {"q": str, "lim": int}

    Returns:
        {"s": "ok|error", "d": {"items": [..]}, "e": {..}|None}

    Expected KB JSONL fields (per line):
        {"id": str, "text": str, "src": str, "d": str|null, "cred": "low|med|high"}
    """
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be an object")
    _load_runtime_env()
    q = (args.get("q") or "").strip()
    lim = args.get("lim")
    if not q:
        return _err("EMPTY_QUERY", "q is required")
    if not isinstance(lim, int) or lim < 1 or lim > 20:
        return _err("BAD_LIMIT", "lim must be 1..20")

    kb_path = os.getenv("KB_PATH")
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if not kb_path:
        kb_path = os.path.join(root, "runtime", "evidence.jsonl")
    if not os.path.isabs(kb_path):
        kb_path = os.path.abspath(os.path.join(root, kb_path))
    if not kb_path or not os.path.isfile(kb_path):
        return _err("KB_NOT_CONFIGURED", "set KB_PATH to a JSONL knowledge base")

    try:
        items = _load_kb(kb_path)
    except Exception as exc:
        return _err("KB_READ_FAIL", str(exc))

    terms = [t for t in q.lower().split() if t]
    scored = []
    for item in items:
        text = item.get("text", "")
        if not text:
            continue
        s = _score(text, terms)
        if s > 0:
            scored.append((s, item))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("id", ""))))

    out = []
    for score, item in scored[:lim]:
        out.append(
            {
                "kid": item.get("id", ""),
                "text": item.get("text", ""),
                "src": item.get("src", ""),
                "d": item.get("d", None),
                "cred": item.get("cred", "low"),
                "score": score,
            }
        )

    return _ok(out)


# Quick test lah
if __name__ == "__main__":
    sample = {"q": "Apollo 11 1969", "lim": 3}
    print(json.dumps(run(sample), ensure_ascii=True))

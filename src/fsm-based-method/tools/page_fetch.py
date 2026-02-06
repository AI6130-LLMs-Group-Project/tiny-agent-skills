### This tool fetches a web page and returns its content up to a specified context limit

import json
import re
import urllib.request


_MAX_BYTES_DEFAULT = 1_000_000


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}}


def _ok(data):
    return {"s": "ok", "d": data, "e": None}


def _detect_charset(content_type):
    if not content_type:
        return "utf-8"
    m = re.search(r"charset=([\w\-]+)", content_type, re.I)
    return m.group(1) if m else "utf-8"


def run(args):
    """
    Args schema:
        {"url": str, "max_bytes": int|null, "timeout": int|null}

    Returns:
        {"s": "ok|error", "d": {"url": str, "status": int, "content_type": str, "text": str}, "e": {..}|None}
    """
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be an object")
    url = (args.get("url") or "").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return _err("BAD_URL", "url must be http or https")
    max_bytes = args.get("max_bytes")
    if max_bytes is None:
        max_bytes = _MAX_BYTES_DEFAULT
    if not isinstance(max_bytes, int) or max_bytes < 1 or max_bytes > 5_000_000:
        return _err("BAD_MAX_BYTES", "max_bytes must be 1..5000000")
    timeout = args.get("timeout")
    if timeout is None:
        timeout = 10
    if not isinstance(timeout, int) or timeout < 1 or timeout > 30:
        return _err("BAD_TIMEOUT", "timeout must be 1..30")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tiny-agent/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read(max_bytes)
            status = getattr(resp, "status", 200)
        charset = _detect_charset(content_type)
        text = raw.decode(charset, errors="replace")
        return _ok({"url": url, "status": status, "content_type": content_type, "text": text})
    except Exception as exc:
        return _err("FETCH_FAIL", str(exc))


# Quick test lah
if __name__ == "__main__":
    sample = {"url": "https://en.wikipedia.org/wiki/Apollo_11", "max_bytes": 20000, "timeout": 10}
    print(json.dumps(run(sample), ensure_ascii=True))

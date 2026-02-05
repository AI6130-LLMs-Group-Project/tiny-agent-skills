# FSM Fact-Verification Method

This module runs the FSM-based fact verification pipeline with llama.cpp and a FastAPI server.
With a wrapper that adopt this system to run on FEVER datasets.

## Prerequisites

- Python 3.10+ (which pydantic wants)
- llama.cpp server running with `/completion` enabled
- `fastapi`, `uvicorn`, `pydantic` installed in your environment

## Configuration

Create `src/fsm-based-method/.env` (copy from `.env.example`) and set:

- `LLM_ENDPOINT=http://127.0.0.1:1025` (llama.cpp server)
- `N_RETRY=2` (max retries for malformed LLM/tool outputs)
- `WEB_SEARCH_PROVIDER=serpapi|tavily` and corresponding API key(s), as a backup from wiki
- `KB_PATH=runtime/evidence.jsonl`
- `TOP_N=3` (Top-N matched sentences picked from source)
- `WIKI_FETCH_LIMIT=2` (per query, expand top wiki pages into sentences)
- `WIKI_MAX_BYTES=200000` and `WIKI_TIMEOUT=10` (page fetch limits)

## Start the API

[Important] Run from the `src/fsm-based-method` directory so local imports resolve:

```bash
cd src/fsm-based-method
uvicorn api:app --host 0.0.0.0 --port 8000
```

## Test the API (I used Postman)

```bash
curl -X POST "http://127.0.0.1:8000/verify" \
  -H "Content-Type: application/json" \
  -d "{\"claim\":\"Newton was born in 1642.\",\"explain\":true,\"trace\":true}"
```

### Response fields
- `decision`: `SUPPORT` | `REFUTE` | `NO ENOUGH INFO`
- `explanation`: only when `explain=true` (includes matched evidence quotes)
- `trace`: only when `trace=true` (state history with metadata)

## FEVER CLI Wrapper

Run batch evaluation (prints steps/system answer/gold answer/cumulative accuracy):

```bash
cd src/fsm-based-method
python fever_runner.py --data data/paper_dev.jsonl --limit 100 --random --seed 234 --show-trace
```

Useful args:
- `--data` can define to a dir where you put the test FEVER dataset jsonl
- `--start N` start offset in JSONL
- `--limit N` number of samples to run
- omit `--show-trace` for concise output
- `--random --seed 123` for picking randomness and random seed for it

## Notes

- Evidence from `search`/`web_search` is appended to `runtime/evidence.jsonl`. This will be used for KB Lookup.
- If no evidence is determined, the decision defaults to `NO ENOUGH INFO`.
- If schema/JSON checks fail repeatedly, the API falls back to `NO ENOUGH INFO` instead of returning 500. (Well, hopefully not tho XD)

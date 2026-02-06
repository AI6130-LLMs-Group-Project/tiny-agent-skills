"""DAG pipeline: fact-checking by directed acyclic graph of skills (query_gen → retrieve → evidence_extract → verify → output)."""

def hello() -> str:
    return "Hello from DAG pipeline!"

import re


def _err(code, msg):
    return {"s": "error", "d": None, "e": {"code": code, "msg": msg}, "rb": "state"}


def _ok(data):
    return {"s": "ok", "d": data, "e": None, "rb": "none"}


_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "to", "of", "in", "on", "at",
    "for", "from", "by", "as", "that", "this", "it", "its", "and", "or", "with", "during", "into", "over",
    "under", "than", "then", "who", "what", "when", "where", "which",
}

_AMBIGUOUS = {
    "lost", "up", "it", "her", "him", "us", "them", "once", "home", "now", "then",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "go", "run", "love", "fall", "rise", "gone", "red", "blue", "black", "white", "green",
}

_FIXED_HINTS = [
    "TV series", "film", "movie", "album", "song", "novel", "book", "band", "episode", "video game",
    "company", "person",
]

_WIKI_HINTS = [
    "TV series", "film", "album", "song", "novel", "book", "video game", "band",
]


def _tokens(text):
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in toks if t not in _STOP]


def _entity_phrases(text):
    if not text:
        return []
    spans = re.findall(r"(?:\b[A-Z][a-z]+\b(?:\s+\b[A-Z][a-z]+\b){0,3})", text)
    mixed = re.findall(r"\b[A-Za-z]*[A-Z][A-Za-z]*\b", text)
    phrases = []
    for span in spans:
        span = span.strip()
        if span and span not in phrases:
            phrases.append(span)
    for token in mixed:
        if len(token) >= 2 and token not in phrases:
            phrases.append(token)
    return phrases


def _predicate_terms(text):
    entities = set(term.lower() for term in _entity_phrases(text))
    terms = []
    for token in _tokens(text):
        if token in entities:
            continue
        terms.append(token)
    return terms


def _ordered_unique(items):
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _numbers(text):
    nums = re.findall(r"\b\d+(?:\.\d+)?\b", text or "")
    return _ordered_unique(nums)


def _is_ambiguous_entity(entity):
    if not entity:
        return False
    if " " in entity:
        return False
    return entity.lower() in _AMBIGUOUS


def _limit_tokens(query, max_tokens=8):
    parts = query.split()
    if len(parts) <= max_tokens:
        return query

    nums = [p for p in parts if re.fullmatch(r"\d+(?:\.\d+)?", p)]
    non_nums = [p for p in parts if p not in nums]

    kept = []
    for token in non_nums:
        if len(kept) >= max_tokens - len(nums):
            break
        kept.append(token)

    out = kept + nums
    return " ".join(out[:max_tokens])


def _build_queries(claim_text):
    entities = _entity_phrases(claim_text)
    predicates = _predicate_terms(claim_text)
    numbers = _numbers(claim_text)
    queries = []

    if entities:
        entity = entities[0].strip()
        if entity:
            base = [entity] + predicates[:2] + numbers
            queries.append(" ".join([t for t in base if t]).strip())
            if predicates:
                queries.append(" ".join([t for t in [entity] + numbers if t]).strip())
    else:
        tokens = _tokens(claim_text)
        if tokens:
            queries.append(" ".join(tokens[:6]))

    if entities and numbers:
        entity = entities[0].strip()
        queries.append(" ".join([t for t in [entity] + numbers if t]).strip())
    if numbers and not entities:
        queries.append(" ".join(numbers + predicates[:2]).strip())

    if entities:
        entity = entities[0].strip()
        if _is_ambiguous_entity(entity):
            # When the entity is vague, we add a little Wikipedia cosplay.
            for hint in _FIXED_HINTS:
                queries.append(" ".join([t for t in [entity, hint] + numbers if t]).strip())
            for hint in _WIKI_HINTS:
                queries.append(" ".join([t for t in [f"{entity} ({hint})"] + numbers if t]).strip())

    queries = [_limit_tokens(q) for q in queries if q]
    return _ordered_unique(queries)[:4]


def run(args):
    if not isinstance(args, dict):
        return _err("BAD_ARGS", "args must be object")

    claims = args.get("claims")
    st = args.get("st") if isinstance(args.get("st"), dict) else {}
    if not isinstance(claims, list) or not claims:
        return _err("NO_CLAIMS", "claims is empty")

    plans = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        cid = claim.get("id", "s1")
        claim_text = claim.get("c", "")
        queries = _build_queries(claim_text)
        if not queries:
            continue
        plans.append({"id": cid, "q": queries, "src": ["wiki", "kb", "web"], "lim": 4})

    if not plans:
        return _err("NO_QUERIES", "no valid query")

    rev = int(st.get("rev", 0)) + 1
    return _ok({"plans": plans, "sp": {"rev": rev, "fsm": "RETRIEVAL"}})

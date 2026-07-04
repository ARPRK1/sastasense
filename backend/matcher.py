"""Product matching & accuracy helpers.

BuyHatke's #1 accuracy complaint is that it matches on loose keywords and shows
unrelated products. We fight that two ways:

1. relevance_score(query, title): every offer is scored against the search query
   and low-relevance junk is dropped before it ever reaches the user.
2. group_key(title): near-identical titles across stores collapse to ONE product
   so the "compare across stores" view lines up the *same* item, not lookalikes.
"""
from __future__ import annotations
import re
import hashlib
from rapidfuzz import fuzz

_STOP = {"the", "with", "and", "for", "new", "latest", "buy", "online", "combo"}
_UNIT = re.compile(r"\b(\d+)\s?(gb|tb|mah|inch|in|cm|ml|l|kg|g|w)\b", re.I)


def _tokens(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return [t for t in text.split() if t and t not in _STOP]


def relevance_score(query: str, title: str) -> float:
    """0-100. How well a listing matches what the user searched for."""
    q, t = query.lower().strip(), title.lower()
    if not q:
        return 100.0
    # token_set_ratio handles word re-ordering and extra marketing words well.
    base = fuzz.token_set_ratio(q, t)
    # Reward when every meaningful query token is present.
    q_tokens = set(_tokens(query))
    if q_tokens:
        present = sum(1 for tok in q_tokens if tok in t)
        coverage = present / len(q_tokens)
        base = 0.6 * base + 0.4 * (coverage * 100)
    # Reward matching capacity/size units (64gb vs 128gb are different products).
    q_units = {m.group(0).lower().replace(" ", "") for m in _UNIT.finditer(query)}
    if q_units:
        t_units = {m.group(0).lower().replace(" ", "") for m in _UNIT.finditer(title)}
        if q_units & t_units:
            base = min(100.0, base + 8)
        elif t_units:                       # different unit present => likely wrong variant
            base -= 12
    return max(0.0, min(100.0, base))


def is_relevant(query: str, title: str, threshold: float = 55.0) -> bool:
    return relevance_score(query, title) >= threshold


def normalise_title(title: str) -> str:
    toks = _tokens(title)
    # keep unit tokens (they carry variant identity) and the first few strong tokens
    units = {m.group(0).lower().replace(" ", "") for m in _UNIT.finditer(title)}
    core = [t for t in toks if len(t) > 2][:6]
    return " ".join(sorted(set(core)) + sorted(units))


def group_key(store: str, title: str) -> str:
    """Stable identity for a listing (used as products.key)."""
    norm = normalise_title(title)
    h = hashlib.sha1(f"{store}|{norm}".encode()).hexdigest()[:16]
    return h


def cross_store_group(title: str) -> str:
    """Identity that ignores the store, so the same item from Amazon & Flipkart
    can be shown side by side."""
    return hashlib.sha1(normalise_title(title).encode()).hexdigest()[:16]

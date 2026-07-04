"""Aggregation layer: run all store scrapers, clean/rank results, persist prices.

This is where the four improvements come together:
- accuracy:   drop irrelevant listings (matcher) + tag every price with freshness
- history:    every observed price is written to price_history
- deal score: compare current price to the item's own history + MRP
- (alerts consume the fresh prices recorded here)
"""
from __future__ import annotations
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import config
import db
import matcher
from models import Offer
from scrapers.amazon_in import AmazonInScraper
from scrapers.flipkart import FlipkartScraper
from scrapers.croma import CromaScraper
from scrapers.reliance_digital import RelianceDigitalScraper
from scrapers.demo import DemoScraper

log = logging.getLogger("aggregator")

_LIVE = {
    "Amazon.in": AmazonInScraper,
    "Flipkart": FlipkartScraper,
    "Croma": CromaScraper,
    "Reliance Digital": RelianceDigitalScraper,
}


def freshness(age_seconds: float) -> str:
    if age_seconds <= config.FRESH_SECONDS:
        return "fresh"
    if age_seconds <= config.STALE_SECONDS:
        return "recent"
    return "stale"


def _search_store(store: str, query: str) -> list[Offer]:
    offers: list[Offer] = []
    if config.LIVE_SCRAPING:
        try:
            offers = _LIVE[store]().safe_search(query)
        except Exception as e:                       # noqa: BLE001
            log.warning("live %s failed: %s", store, e)
    if not offers and config.DEMO_FALLBACK:
        offers = DemoScraper(store).safe_search(query)
    return offers


def deal_score(price, stats: dict, mrp) -> dict:
    """Turn history into a plain-English 'is this a genuine deal?' verdict.

    Directly answers BuyHatke's most-loved use case: 'is the discount real or an
    inflated-MRP trick?'  Uses the item's OWN observed prices, not the MRP.
    """
    lowest, median = stats.get("lowest"), stats.get("median")
    verdict, label = "unknown", "Not enough history yet"
    if price and lowest and median:
        if price <= lowest * 1.01:
            verdict, label = "great", "Lowest price we've seen"
        elif price <= median * 0.95:
            verdict, label = "good", "Below its usual price"
        elif price <= median * 1.02:
            verdict, label = "typical", "Around its usual price"
        else:
            verdict, label = "high", "Pricier than usual"
    # Flag inflated-MRP discounts (big MRP gap but not actually cheap historically)
    inflated = bool(mrp and median and mrp > median * 1.25 and price and price >= median)
    return {"verdict": verdict, "label": label, "inflated_mrp": inflated,
            "lowest": lowest, "median": median}


def search(query: str) -> dict:
    """Full search -> ranked, de-duplicated, history-aware results."""
    stores = list(_LIVE.keys())
    with ThreadPoolExecutor(max_workers=len(stores)) as ex:
        results = list(ex.map(lambda s: _search_store(s, query), stores))

    all_offers: list[Offer] = []
    for store_offers in results:
        for o in store_offers:
            if o.price is None:
                continue
            if not matcher.is_relevant(query, o.title):
                continue
            all_offers.append(o)

    live_count = sum(1 for o in all_offers if o.source == "live")
    items = []
    for o in all_offers:
        key = matcher.group_key(o.store, o.title)
        pid = db.upsert_product(key, o.store, o.title, o.url, o.image)
        db.record_price(pid, o.price, o.mrp, o.in_stock, o.source)
        stats = db.price_stats(pid)
        d = o.to_dict()
        d["product_id"] = pid
        d["group"] = matcher.cross_store_group(o.title)
        d["relevance"] = round(matcher.relevance_score(query, o.title))
        d["freshness"] = freshness(d["age_seconds"])
        d["deal"] = deal_score(o.price, stats, o.mrp)
        items.append(d)

    # Sort: relevance first, then cheapest.
    items.sort(key=lambda x: (-x["relevance"], x["price"]))

    best = min((i["price"] for i in items), default=None)
    for i in items:
        i["is_best_price"] = (i["price"] == best)

    return {
        "query": query,
        "count": len(items),
        "live_results": live_count,
        "using_demo": live_count == 0,
        "generated_at": time.time(),
        "items": items,
    }


def refresh_product(product_id: int) -> dict | None:
    """Re-fetch one tracked product's current price and record it (for alerts)."""
    p = db.get_product(product_id)
    if not p:
        return None
    res = search(p["title"])
    for i in res["items"]:
        if i["product_id"] == product_id:
            return i
    # Fall back to the closest match in the same store.
    for i in res["items"]:
        if i["store"] == p["store"]:
            return i
    return None

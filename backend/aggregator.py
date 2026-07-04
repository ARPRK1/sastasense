"""Aggregation layer: run store scrapers, clean/rank results, persist prices.

Ranking rule (fixes the 'fake product' bug):
  * LIVE results always take priority. Demo/sample data is used ONLY when every
    live store returned nothing, and is clearly labelled. Demo never mixes with,
    or outranks, real listings.
"""
from __future__ import annotations
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

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

# Curated browse categories (each maps to a search term the engine understands).
CATEGORIES = [
    {"label": "Mobiles", "icon": "📱", "q": "smartphone"},
    {"label": "Laptops", "icon": "💻", "q": "laptop"},
    {"label": "Headphones", "icon": "🎧", "q": "headphone"},
    {"label": "Smartwatches", "icon": "⌚", "q": "smartwatch"},
    {"label": "Televisions", "icon": "📺", "q": "tv"},
    {"label": "Tablets", "icon": "📲", "q": "ipad"},
    {"label": "Air Conditioners", "icon": "❄️", "q": "ac"},
    {"label": "Home Appliances", "icon": "🧺", "q": "washing machine"},
]


def affiliate_url(store: str, url: str) -> str:
    """Turn a plain store link into a commission-earning one.

    Amazon.in gets the Associates tag appended directly (best rates). Other
    stores are monetised automatically by the Cuelinks script on the frontend,
    so their URLs are returned unchanged here."""
    try:
        if store == "Amazon.in" and config.AMAZON_ASSOC_TAG and "amazon." in url:
            p = urlparse(url)
            q = dict(parse_qsl(p.query))
            q["tag"] = config.AMAZON_ASSOC_TAG
            return urlunparse(p._replace(query=urlencode(q)))
    except Exception:                                 # noqa: BLE001
        pass
    return url


def freshness(age_seconds: float) -> str:
    if age_seconds <= config.FRESH_SECONDS:
        return "fresh"
    if age_seconds <= config.STALE_SECONDS:
        return "recent"
    return "stale"


def _live_store(store: str, query: str) -> list[Offer]:
    try:
        return _LIVE[store]().safe_search(query)
    except Exception as e:                            # noqa: BLE001
        log.warning("live %s failed: %s", store, e)
        return []


def _relevant_priced(query: str, offers: list[Offer]) -> list[Offer]:
    out = []
    for o in offers:
        if o.price is None:
            continue
        if not matcher.is_relevant(query, o.title):
            continue
        out.append(o)
    return out


def deal_score(price, stats: dict, mrp) -> dict:
    """Plain-English 'is this a genuine deal?' verdict from the item's OWN history.

    Needs a few data points before it will make a confident claim, so brand-new
    items say 'Building price history' instead of falsely 'Lowest ever'.
    """
    lowest, median, count = stats.get("lowest"), stats.get("median"), stats.get("count", 0)
    if not price or count < 4 or not lowest or not median:
        return {"verdict": "new", "label": "Building price history",
                "inflated_mrp": False, "lowest": lowest, "median": median}
    if price <= lowest * 1.01:
        verdict, label = "great", "Lowest price we've seen"
    elif price <= median * 0.95:
        verdict, label = "good", "Below its usual price"
    elif price <= median * 1.02:
        verdict, label = "typical", "Around its usual price"
    else:
        verdict, label = "high", "Pricier than usual"
    inflated = bool(mrp and median and mrp > median * 1.25 and price >= median)
    return {"verdict": verdict, "label": label, "inflated_mrp": inflated,
            "lowest": lowest, "median": median}


def search(query: str) -> dict:
    """Full search -> ranked, de-duplicated, history-aware results (live-first)."""
    stores = list(_LIVE.keys())

    # 1) Try LIVE across all stores in parallel.
    with ThreadPoolExecutor(max_workers=len(stores)) as ex:
        live_lists = list(ex.map(lambda s: _live_store(s, query), stores))
    live_offers = _relevant_priced(query, [o for lst in live_lists for o in lst])

    # 2) Only if NOTHING came back live, fall back to labelled demo data.
    using_demo = False
    if live_offers:
        offers = live_offers
    elif config.DEMO_FALLBACK:
        demo = []
        for s in stores:
            demo += DemoScraper(s).safe_search(query)
        offers = _relevant_priced(query, demo)
        using_demo = bool(offers)
    else:
        offers = []

    items = []
    for o in offers:
        key = matcher.group_key(o.store, o.title)
        pid = db.upsert_product(key, o.store, o.title, o.url, o.image)
        db.record_price(pid, o.price, o.mrp, o.in_stock, o.source)
        stats = db.price_stats(pid)
        d = o.to_dict()
        d["url"] = affiliate_url(o.store, d["url"])
        d["product_id"] = pid
        d["group"] = matcher.cross_store_group(o.title)
        d["relevance"] = round(matcher.relevance_score(query, o.title))
        d["freshness"] = freshness(d["age_seconds"])
        d["deal"] = deal_score(o.price, stats, o.mrp)
        items.append(d)

    items.sort(key=lambda x: (-x["relevance"], x["price"]))
    best = min((i["price"] for i in items), default=None)
    for i in items:
        i["is_best_price"] = (i["price"] == best)

    return {
        "query": query,
        "count": len(items),
        "live_results": 0 if using_demo else len(items),
        "using_demo": using_demo,
        "generated_at": time.time(),
        "items": items,
    }


def refresh_product(product_id: int) -> dict | None:
    p = db.get_product(product_id)
    if not p:
        return None
    res = search(p["title"])
    for i in res["items"]:
        if i["product_id"] == product_id:
            return i
    for i in res["items"]:
        if i["store"] == p["store"]:
            return i
    return None

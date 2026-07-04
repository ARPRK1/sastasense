"""Deterministic demo provider.

Generates realistic, query-relevant products with believable per-store price
spreads so the ENTIRE app (search, compare, history charts, deal score, alerts)
is fully demonstrable even when live scraping is blocked. Deterministic = the
same query always yields the same catalogue, so price history accumulates
sensibly across refreshes instead of jumping randomly.
"""
from __future__ import annotations
import hashlib
import random
import time

from models import Offer
import config

# A small catalogue of realistic Indian-market products, keyed by category words.
_CATALOG = {
    "iphone": [
        ("Apple iPhone 15 (128GB) - Black", 79900),
        ("Apple iPhone 15 Plus (128GB) - Blue", 89900),
        ("Apple iPhone 14 (128GB) - Midnight", 69900),
    ],
    "samsung": [
        ("Samsung Galaxy S24 5G (256GB) - Onyx Black", 74999),
        ("Samsung Galaxy S23 FE 5G (128GB) - Mint", 44999),
        ("Samsung Galaxy A55 5G (128GB) - Iceblue", 39999),
    ],
    "laptop": [
        ("HP Pavilion 15 Intel Core i5 12th Gen (16GB/512GB)", 62990),
        ("Lenovo IdeaPad Slim 3 Ryzen 5 (8GB/512GB)", 44990),
        ("ASUS Vivobook 15 Core i3 (8GB/512GB)", 33990),
    ],
    "headphone": [
        ("Sony WH-1000XM5 Wireless Noise Cancelling Headphones", 26990),
        ("boAt Rockerz 450 Bluetooth On-Ear Headphones", 1499),
        ("JBL Tune 760NC Wireless Over-Ear Headphones", 5999),
    ],
    "watch": [
        ("Apple Watch SE (2nd Gen) GPS 40mm", 29900),
        ("Noise ColorFit Pro 5 Smart Watch", 3999),
        ("boAt Wave Call 2 Smart Watch", 1799),
    ],
    "tv": [
        ("Samsung 55-inch Crystal 4K UHD Smart TV", 47990),
        ("LG 43-inch 4K Ultra HD Smart LED TV", 31990),
        ("Mi 5A 40-inch Full HD Smart LED TV", 22999),
    ],
}
_STORE_BIAS = {  # each store prices a bit differently
    "Amazon.in": 1.00,
    "Flipkart": 0.98,
    "Croma": 1.03,
    "Reliance Digital": 1.02,
}
_IMG = "https://via.placeholder.com/120x120.png?text={}"


def _pick_products(query: str):
    q = query.lower()
    for key, items in _CATALOG.items():
        if key in q:
            return items
    # Generic fallback: synthesise 3 plausible items from the query words.
    base = query.strip().title() or "Product"
    seed = int(hashlib.sha1(q.encode()).hexdigest(), 16) % 9000 + 1000
    return [
        (f"{base} - Model A", seed),
        (f"{base} - Model B (Premium)", int(seed * 1.4)),
        (f"{base} - Model C (Budget)", int(seed * 0.7)),
    ]


def _price_for(base_price: int, store: str, title: str, when: float) -> float:
    """Stable-ish price with a slow time wobble so history looks real."""
    h = int(hashlib.sha1(f"{store}{title}".encode()).hexdigest(), 16)
    rng = random.Random(h)
    bias = _STORE_BIAS.get(store, 1.0) * (1 + rng.uniform(-0.03, 0.03))
    # gentle deterministic wave over ~30-day period
    day = int(when // 86400)
    wave = 1 + 0.05 * ((day % 30) - 15) / 15.0
    return round(base_price * bias * wave, 0)


class DemoScraper:
    store_name = "demo"

    def __init__(self, store: str):
        self.store = store

    def safe_search(self, query: str) -> list[Offer]:
        now = time.time()
        offers = []
        for title, base in _pick_products(query):
            price = _price_for(base, self.store, title, now)
            mrp = round(price * random.Random(int(base)).uniform(1.05, 1.35), 0)
            offers.append(Offer(
                store=self.store,
                title=title,
                price=price,
                mrp=max(mrp, price),
                url=f"https://example-demo.local/{self.store}/"
                    f"{hashlib.sha1(title.encode()).hexdigest()[:10]}",
                image=_IMG.format(self.store.split(".")[0].replace(" ", "+")),
                rating=round(random.Random(int(base)).uniform(3.6, 4.8), 1),
                in_stock=True,
                source="demo",
            ))
        return offers[: config.MAX_RESULTS_PER_STORE]

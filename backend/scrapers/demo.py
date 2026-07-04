"""Realistic demo/sample provider.

Used ONLY as a clearly-labelled safety net when live scraping returns nothing
(e.g. every store blocked the server). It NEVER fabricates arbitrary products or
prices any more: it only returns items from a curated catalogue of real
India-market products with believable prices. Unknown queries return nothing,
so the app shows an honest "no live results" state instead of nonsense.
"""
from __future__ import annotations
import hashlib
import random
import time

from models import Offer
import config

# Curated catalogue of real India-market products with realistic price anchors.
# Keyed by trigger words found in the query. Prices are indicative (INR).
_CATALOG = {
    "iphone 15": [("Apple iPhone 15 (128GB)", 71999), ("Apple iPhone 15 Plus (128GB)", 81999)],
    "iphone": [("Apple iPhone 15 (128GB)", 71999), ("Apple iPhone 14 (128GB)", 57999)],
    "pixel 8": [("Google Pixel 8 (128GB)", 54999), ("Google Pixel 8 Pro (256GB)", 89999)],
    "pixel 7": [("Google Pixel 7 (128GB)", 39999), ("Google Pixel 7 Pro (128GB)", 56999)],
    "pixel": [("Google Pixel 8 (128GB)", 54999), ("Google Pixel 7a (128GB)", 34999)],
    "oneplus": [("OnePlus 12R (128GB)", 39999), ("OnePlus Nord CE4 (128GB)", 24999)],
    "nothing phone": [("Nothing Phone (2a) 128GB", 23999), ("Nothing Phone (2) 256GB", 39999)],
    "samsung galaxy s24": [("Samsung Galaxy S24 5G (256GB)", 74999)],
    "samsung galaxy": [("Samsung Galaxy S24 5G (256GB)", 74999), ("Samsung Galaxy A55 5G (128GB)", 39999)],
    "samsung": [("Samsung Galaxy S24 5G (256GB)", 74999), ("Samsung Galaxy A35 5G (128GB)", 30999)],
    "redmi": [("Redmi Note 13 Pro 5G (128GB)", 25999), ("Redmi 13C (128GB)", 10999)],
    "realme": [("realme 12 Pro+ 5G (256GB)", 29999), ("realme Narzo 70 5G (128GB)", 15999)],
    "laptop": [("HP Pavilion 15 Core i5 12th Gen (16GB/512GB)", 62990),
               ("Lenovo IdeaPad Slim 3 Ryzen 5 (8GB/512GB)", 44990)],
    "macbook": [("Apple MacBook Air M2 (8GB/256GB)", 89990), ("Apple MacBook Air M1 (8GB/256GB)", 69990)],
    "headphone": [("Sony WH-1000XM5 Wireless Noise Cancelling", 26990),
                  ("JBL Tune 760NC Wireless Over-Ear", 5999)],
    "earbuds": [("Apple AirPods (3rd Gen)", 16900), ("boAt Airdopes 141", 1299)],
    "airpods": [("Apple AirPods (3rd Gen)", 16900), ("Apple AirPods Pro (2nd Gen)", 21900)],
    "watch": [("Apple Watch SE (2nd Gen) GPS 40mm", 29900), ("Noise ColorFit Pro 5", 3999)],
    "smartwatch": [("Apple Watch SE (2nd Gen) GPS 40mm", 29900), ("boAt Wave Call 2", 1799)],
    "tv": [("Samsung 55-inch Crystal 4K UHD Smart TV", 47990),
           ("LG 43-inch 4K Ultra HD Smart LED TV", 31990)],
    "ipad": [("Apple iPad 10th Gen (64GB) Wi-Fi", 34900), ("Apple iPad Air M2 (128GB)", 59900)],
    "ac": [("LG 1.5 Ton 5 Star Inverter Split AC", 46990), ("Voltas 1.5 Ton 3 Star Split AC", 33990)],
    "refrigerator": [("Samsung 253L 3 Star Double Door Fridge", 26490)],
    "washing machine": [("LG 7Kg 5 Star Fully-Automatic Front Load", 33990)],
}
_STORE_BIAS = {"Amazon.in": 1.00, "Flipkart": 0.985, "Croma": 1.03, "Reliance Digital": 1.02}
_IMG = "https://via.placeholder.com/120x120.png?text={}"


def _pick_products(query: str):
    q = query.lower().strip()
    # Prefer the most specific catalogue key contained in the query.
    for key in sorted(_CATALOG, key=len, reverse=True):
        if key in q:
            return _CATALOG[key]
    return []                       # unknown -> no fabricated products


def _price_for(base_price: int, store: str, title: str, when: float) -> float:
    h = int(hashlib.sha1(f"{store}{title}".encode()).hexdigest(), 16)
    rng = random.Random(h)
    bias = _STORE_BIAS.get(store, 1.0) * (1 + rng.uniform(-0.02, 0.02))
    day = int(when // 86400)
    wave = 1 + 0.04 * ((day % 30) - 15) / 15.0     # gentle 30-day wave for history
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
            mrp = round(base * random.Random(int(base)).uniform(1.06, 1.18), 0)
            offers.append(Offer(
                store=self.store, title=title, price=price, mrp=max(mrp, price),
                url=f"https://www.google.com/search?q="
                    + title.replace(" ", "+") + f"+{self.store.replace(' ', '+')}+price",
                image=_IMG.format(self.store.split(".")[0].replace(" ", "+")),
                rating=round(random.Random(int(base)).uniform(3.9, 4.7), 1),
                in_stock=True, source="demo",
            ))
        return offers[: config.MAX_RESULTS_PER_STORE]

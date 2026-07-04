"""Shared data structures used across scrapers and the API."""
from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Offer:
    """A single product listing from one store."""
    store: str
    title: str
    price: Optional[float]          # current price in INR, None if unavailable
    url: str
    image: str = ""
    mrp: Optional[float] = None     # original / struck-through price
    rating: Optional[float] = None
    in_stock: bool = True
    fetched_at: float = field(default_factory=lambda: time.time())
    source: str = "live"            # "live" or "demo"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["discount_pct"] = self.discount_pct
        d["age_seconds"] = round(time.time() - self.fetched_at)
        return d

    @property
    def discount_pct(self) -> Optional[int]:
        if self.mrp and self.price and self.mrp > self.price:
            return round((self.mrp - self.price) / self.mrp * 100)
        return None

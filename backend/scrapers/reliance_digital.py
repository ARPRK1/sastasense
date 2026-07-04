"""Reliance Digital search scraper.

Like Croma, listings are partly client-rendered. Defensive parse + demo fallback.
"""
from __future__ import annotations
import re
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup

from .base import BaseScraper, parse_price
from models import Offer

BASE = "https://www.reliancedigital.in"
_PRICE_RE = re.compile(r"₹\s?[\d,]+")


class RelianceDigitalScraper(BaseScraper):
    store_name = "Reliance Digital"

    def search(self, query: str) -> list[Offer]:
        url = f"{BASE}/search?" + urlencode({"q": query})
        r = self.get(url)
        if not r:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        offers: list[Offer] = []
        for card in soup.select("div.sp.grid, li.grid, div.product-card"):
            link = card.select_one("a[href]")
            title_el = card.select_one("p.sp__name, .product-title, h3")
            if not link or not title_el:
                continue
            text = card.get_text(" ", strip=True)
            prices = _PRICE_RE.findall(text)
            price = parse_price(prices[0]) if prices else None
            img = card.select_one("img")
            offers.append(Offer(
                store=self.store_name,
                title=title_el.get_text(strip=True)[:160],
                price=price,
                mrp=parse_price(prices[1]) if len(prices) > 1 else None,
                url=urljoin(BASE, link.get("href", "")),
                image=img.get("src") or img.get("data-src", "") if img else "",
                in_stock=price is not None,
                source="live",
            ))
        return offers

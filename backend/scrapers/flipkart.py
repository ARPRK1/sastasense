"""Flipkart search scraper.

Flipkart's markup uses obfuscated, frequently-changing class names, so this
parser is intentionally defensive: it finds anchors to product pages, then reads
the nearest price-looking text. Returns [] if the layout changed or was blocked.
"""
from __future__ import annotations
import re
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup

from .base import BaseScraper, parse_price
from models import Offer

BASE = "https://www.flipkart.com"
_PRICE_RE = re.compile(r"₹\s?[\d,]+")


class FlipkartScraper(BaseScraper):
    store_name = "Flipkart"

    def search(self, query: str) -> list[Offer]:
        url = f"{BASE}/search?" + urlencode({"q": query})
        r = self.get(url)
        if not r:
            return []
        soup = BeautifulSoup(r.text, "lxml")
        offers: list[Offer] = []
        seen = set()
        for a in soup.select('a[href*="/p/"]'):
            href = a.get("href", "")
            if not href or href in seen:
                continue
            title = a.get("title") or a.get_text(" ", strip=True)
            if not title or len(title) < 6:
                continue
            # Search upward for the card container holding the price.
            card = a
            for _ in range(4):
                if card.parent:
                    card = card.parent
            text = card.get_text(" ", strip=True)
            prices = _PRICE_RE.findall(text)
            if not prices:
                continue
            seen.add(href)
            price = parse_price(prices[0])
            mrp = parse_price(prices[1]) if len(prices) > 1 else None
            img = card.select_one("img")
            offers.append(Offer(
                store=self.store_name,
                title=title[:160],
                price=price,
                mrp=mrp if (mrp and price and mrp > price) else None,
                url=urljoin(BASE, href),
                image=img.get("src", "") if img else "",
                in_stock=price is not None,
                source="live",
            ))
            if len(offers) >= 12:
                break
        return offers

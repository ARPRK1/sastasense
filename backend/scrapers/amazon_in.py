"""Amazon.in search scraper.

NOTE: Amazon aggressively blocks automated traffic, especially from datacentre
IPs. This parser targets the standard search-results layout and returns [] when
blocked (a CAPTCHA / robot page), letting the aggregator fall back to demo data.
Run from a residential connection for best live results.
"""
from __future__ import annotations
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup

from .base import BaseScraper, parse_price
from models import Offer

BASE = "https://www.amazon.in"


class AmazonInScraper(BaseScraper):
    store_name = "Amazon.in"

    def search(self, query: str) -> list[Offer]:
        url = f"{BASE}/s?" + urlencode({"k": query})
        r = self.get(url)
        if not r or "captcha" in r.text.lower():
            return []
        soup = BeautifulSoup(r.text, "lxml")
        offers: list[Offer] = []
        for card in soup.select('div[data-component-type="s-search-result"]'):
            title_el = card.select_one("h2 a span") or card.select_one("h2 span")
            link_el = card.select_one("h2 a") or card.select_one("a.a-link-normal")
            if not title_el or not link_el:
                continue
            price_el = card.select_one("span.a-price > span.a-offscreen")
            mrp_el = card.select_one(
                "span.a-price.a-text-price > span.a-offscreen")
            img_el = card.select_one("img.s-image")
            rating_el = card.select_one("span.a-icon-alt")
            price = parse_price(price_el.get_text()) if price_el else None
            offers.append(Offer(
                store=self.store_name,
                title=title_el.get_text(strip=True),
                price=price,
                mrp=parse_price(mrp_el.get_text()) if mrp_el else None,
                url=urljoin(BASE, link_el.get("href", "")),
                image=img_el.get("src", "") if img_el else "",
                rating=parse_price(rating_el.get_text()) if rating_el else None,
                in_stock=price is not None,
                source="live",
            ))
        return offers

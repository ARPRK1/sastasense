"""Base scraper: shared HTTP client, price parsing and safety wrapper.

Every real store scraper subclasses BaseScraper and implements search().
The .safe_search() wrapper guarantees a scraper can never crash the app:
any network block, layout change or timeout returns [] and is logged, and the
aggregator then fills the gap from the demo provider.
"""
from __future__ import annotations
import re
import logging
import httpx

import config
from models import Offer

log = logging.getLogger("scraper")


def parse_price(text: str):
    """'₹1,29,900.00' -> 129900.0 ; returns None if nothing numeric."""
    if not text:
        return None
    m = re.search(r"[\d,]+(?:\.\d+)?", text.replace("\xa0", " "))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


class BaseScraper:
    store_name: str = "base"

    def __init__(self, client: httpx.Client | None = None):
        self._client = client

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers=config.DEFAULT_HEADERS,
                timeout=config.REQUEST_TIMEOUT,
                follow_redirects=True,
            )
        return self._client

    def get(self, url: str, params: dict | None = None) -> httpx.Response | None:
        try:
            r = self.client.get(url, params=params)
            if r.status_code == 200 and len(r.text) > 500:
                return r
            log.warning("%s: bad response %s (%d bytes)",
                        self.store_name, r.status_code, len(r.text))
        except Exception as e:                       # noqa: BLE001
            log.warning("%s: request failed: %s", self.store_name, e)
        return None

    def search(self, query: str) -> list[Offer]:
        raise NotImplementedError

    def safe_search(self, query: str) -> list[Offer]:
        try:
            offers = self.search(query) or []
        except Exception as e:                        # noqa: BLE001
            log.warning("%s: search error: %s", self.store_name, e)
            offers = []
        return offers[: config.MAX_RESULTS_PER_STORE]

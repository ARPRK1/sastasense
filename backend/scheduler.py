"""Background job: periodically refresh watch-listed products and fire alerts.

Keeping tracked prices current in the background is what makes alerts fire on
time - the reliability gap users reported with BuyHatke.
"""
from __future__ import annotations
import logging
from apscheduler.schedulers.background import BackgroundScheduler

import config
import db
import aggregator
import alerts

log = logging.getLogger("scheduler")
_scheduler: BackgroundScheduler | None = None


def refresh_tracked() -> None:
    watched = db.watchlist()
    log.info("refreshing %d tracked product(s)", len(watched))
    for p in watched:
        try:
            aggregator.refresh_product(p["id"])
        except Exception as e:                        # noqa: BLE001
            log.warning("refresh failed for %s: %s", p["id"], e)
    alerts.check_all()


def start() -> BackgroundScheduler:
    global _scheduler
    if _scheduler:
        return _scheduler
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(refresh_tracked, "interval",
                       minutes=config.REFRESH_INTERVAL_MIN, id="refresh")
    _scheduler.start()
    log.info("scheduler started (every %d min)", config.REFRESH_INTERVAL_MIN)
    return _scheduler

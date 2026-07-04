"""Alert evaluation + optional e-mail notification.

Reliability was BuyHatke's main alert complaint, so the logic here is simple and
deterministic: on every refresh we compare each active alert against the latest
recorded price and fire immediately when the condition is met. Multiple alerts
per product (e.g. notify at 4599 AND at 4399) are fully supported.
"""
from __future__ import annotations
import logging
import smtplib
from email.mime.text import MIMEText

import config
import db

log = logging.getLogger("alerts")


def _send_email(to: str, subject: str, body: str) -> bool:
    if not (config.SMTP_HOST and config.SMTP_USER and to):
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = config.ALERT_FROM
        msg["To"] = to
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
            s.starttls()
            s.login(config.SMTP_USER, config.SMTP_PASS)
            s.sendmail(config.ALERT_FROM, [to], msg.as_string())
        return True
    except Exception as e:                            # noqa: BLE001
        log.warning("email send failed: %s", e)
        return False


def _latest_price(product_id: int):
    hist = db.history(product_id)
    if not hist:
        return None, True
    last = hist[-1]
    return last["price"], bool(last["in_stock"])


def check_all() -> list[dict]:
    """Evaluate every active alert. Returns the list of alerts that just fired."""
    fired = []
    for a in db.active_alerts():
        price, in_stock = _latest_price(a["product_id"])
        if price is None:
            continue
        hit = False
        if a["kind"] == "price" and a["target_price"] is not None:
            hit = price <= a["target_price"] and in_stock
        elif a["kind"] == "stock":
            hit = in_stock
        if not hit:
            continue
        db.mark_triggered(a["id"])
        prod = db.get_product(a["product_id"])
        info = {
            "alert_id": a["id"],
            "product_id": a["product_id"],
            "title": prod["title"] if prod else "",
            "kind": a["kind"],
            "target_price": a["target_price"],
            "price": price,
            "url": prod["url"] if prod else "",
        }
        fired.append(info)
        if a["email"]:
            body = (f"Good news! '{info['title']}' is now ₹{price:,.0f}"
                    + (f" (your target was ₹{a['target_price']:,.0f})."
                       if a["kind"] == "price" else " and back in stock.")
                    + f"\n\nBuy: {info['url']}")
            _send_email(a["email"], "Price alert triggered", body)
    if fired:
        log.info("%d alert(s) fired", len(fired))
    return fired

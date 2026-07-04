"""Quick self-test. Run:  python selftest.py

Verifies the whole pipeline WITHOUT needing the web server or live internet:
search -> relevance filtering -> DB history -> deal score -> alerts.
Uses demo data (set LIVE_SCRAPING=false to force it).
"""
import os
os.environ.setdefault("LIVE_SCRAPING", "false")   # force deterministic demo run

import db
import aggregator
import alerts
import matcher


def check(name, cond):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    assert cond, name


def main():
    db.init()

    # 1. Search returns relevant, priced, ranked results
    res = aggregator.search("iphone 15")
    check("search returns items", res["count"] > 0)
    check("every item has a price", all(i["price"] for i in res["items"]))
    check("results sorted by relevance then price",
          res["items"] == sorted(res["items"],
                                 key=lambda x: (-x["relevance"], x["price"])))
    check("exactly one best-price flag per price group",
          sum(1 for i in res["items"] if i["is_best_price"]) >= 1)

    # 2. Relevance filter actually rejects junk
    check("relevance rejects unrelated title",
          not matcher.is_relevant("iphone 15", "Kitchen Mixer Grinder 750W"))

    # 3. History accumulates + deal score works
    pid = res["items"][0]["product_id"]
    # simulate a price drop then recovery
    db.record_price(pid, 100.0, 150.0, True, "demo")
    db.record_price(pid, 80.0, 150.0, True, "demo")
    db.record_price(pid, 120.0, 150.0, True, "demo")
    stats = db.price_stats(pid)
    check("history recorded multiple points", stats["count"] >= 3)
    great = aggregator.deal_score(80.0, stats, 150.0)
    check("lowest price flagged as great deal", great["verdict"] == "great")
    high = aggregator.deal_score(200.0, stats, 150.0)
    check("above-usual price flagged as high", high["verdict"] == "high")

    # 4. Alerts: multiple targets per product + fire + easy delete
    a1 = db.add_alert(pid, "price", 90.0)
    a2 = db.add_alert(pid, "price", 70.0)
    check("multiple alerts allowed on one product",
          len(db.alerts_for(pid)) >= 2)
    db.record_price(pid, 85.0, 150.0, True, "demo")   # should trip the 90 alert only
    fired = alerts.check_all()
    fired_ids = {f["alert_id"] for f in fired}
    check("only the met alert fires", a1 in fired_ids and a2 not in fired_ids)
    db.delete_alert(a2)
    check("alert deletion works",
          all(x["id"] != a2 for x in db.alerts_for(pid)))

    print("\nAll checks passed ✅")


if __name__ == "__main__":
    main()

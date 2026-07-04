"""SQLite persistence: products, full price history, watchlist and alerts.

Design notes tied to the BuyHatke improvements:
- price_history stores EVERY observed price with a timestamp -> real charts +
  a trustworthy "is this discount genuine?" judgement (lowest / median).
- alerts allows MULTIPLE target prices per product and easy deletion -> fixes
  the two most-cited alert complaints.
"""
from __future__ import annotations
import sqlite3
import time
import threading
from typing import Optional

import config

_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL;")
    return _local.conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    key          TEXT UNIQUE,          -- normalised identity (store + title hash)
    store        TEXT,
    title        TEXT,
    url          TEXT,
    image        TEXT,
    created_at   REAL
);

CREATE TABLE IF NOT EXISTS price_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER,
    price        REAL,
    mrp          REAL,
    in_stock     INTEGER,
    source       TEXT,
    ts           REAL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
CREATE INDEX IF NOT EXISTS idx_hist_pid ON price_history(product_id, ts);

CREATE TABLE IF NOT EXISTS watchlist (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER UNIQUE,
    added_at     REAL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER,
    kind          TEXT,      -- 'price' or 'stock'
    target_price  REAL,      -- for kind='price'
    email         TEXT,      -- optional; blank => in-app only
    active        INTEGER DEFAULT 1,
    triggered_at  REAL,      -- NULL until it fires
    created_at    REAL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""


def init() -> None:
    _conn().executescript(SCHEMA)
    _conn().commit()


# ----------------------------------------------------------------- products
def upsert_product(key: str, store: str, title: str, url: str, image: str) -> int:
    c = _conn()
    row = c.execute("SELECT id FROM products WHERE key=?", (key,)).fetchone()
    if row:
        c.execute("UPDATE products SET title=?, url=?, image=? WHERE id=?",
                  (title, url, image, row["id"]))
        c.commit()
        return row["id"]
    cur = c.execute(
        "INSERT INTO products(key, store, title, url, image, created_at) "
        "VALUES(?,?,?,?,?,?)",
        (key, store, title, url, image, time.time()),
    )
    c.commit()
    return cur.lastrowid


def get_product(product_id: int) -> Optional[sqlite3.Row]:
    return _conn().execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()


# ------------------------------------------------------------- price history
def record_price(product_id: int, price, mrp, in_stock: bool, source: str) -> None:
    """Only appends a row when the price actually changed (keeps charts clean)."""
    c = _conn()
    last = c.execute(
        "SELECT price FROM price_history WHERE product_id=? ORDER BY ts DESC LIMIT 1",
        (product_id,),
    ).fetchone()
    if last is not None and last["price"] == price:
        return
    c.execute(
        "INSERT INTO price_history(product_id, price, mrp, in_stock, source, ts) "
        "VALUES(?,?,?,?,?,?)",
        (product_id, price, mrp, 1 if in_stock else 0, source, time.time()),
    )
    c.commit()


def history(product_id: int) -> list[dict]:
    rows = _conn().execute(
        "SELECT price, mrp, in_stock, ts FROM price_history "
        "WHERE product_id=? ORDER BY ts ASC",
        (product_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def price_stats(product_id: int) -> dict:
    """Lowest / highest / median observed price -> 'genuine deal?' judgement."""
    rows = _conn().execute(
        "SELECT price FROM price_history WHERE product_id=? AND price IS NOT NULL "
        "ORDER BY price ASC",
        (product_id,),
    ).fetchall()
    prices = [r["price"] for r in rows]
    if not prices:
        return {"lowest": None, "highest": None, "median": None, "count": 0}
    n = len(prices)
    median = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
    return {"lowest": prices[0], "highest": prices[-1], "median": median, "count": n}


# ---------------------------------------------------------------- watchlist
def add_to_watchlist(product_id: int) -> None:
    c = _conn()
    c.execute("INSERT OR IGNORE INTO watchlist(product_id, added_at) VALUES(?,?)",
              (product_id, time.time()))
    c.commit()


def remove_from_watchlist(product_id: int) -> None:
    c = _conn()
    c.execute("DELETE FROM watchlist WHERE product_id=?", (product_id,))
    c.commit()


def watchlist() -> list[sqlite3.Row]:
    return _conn().execute(
        "SELECT p.* FROM watchlist w JOIN products p ON p.id=w.product_id "
        "ORDER BY w.added_at DESC"
    ).fetchall()


# ------------------------------------------------------------------- alerts
def add_alert(product_id: int, kind: str, target_price, email: str = "") -> int:
    c = _conn()
    cur = c.execute(
        "INSERT INTO alerts(product_id, kind, target_price, email, active, created_at) "
        "VALUES(?,?,?,?,1,?)",
        (product_id, kind, target_price, email, time.time()),
    )
    c.commit()
    return cur.lastrowid


def delete_alert(alert_id: int) -> None:
    c = _conn()
    c.execute("DELETE FROM alerts WHERE id=?", (alert_id,))   # easy delete -> fixes complaint
    c.commit()


def alerts_for(product_id: int) -> list[dict]:
    rows = _conn().execute(
        "SELECT * FROM alerts WHERE product_id=? ORDER BY created_at DESC",
        (product_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def active_alerts() -> list[sqlite3.Row]:
    return _conn().execute("SELECT * FROM alerts WHERE active=1").fetchall()


def all_alerts_with_product() -> list[dict]:
    rows = _conn().execute(
        "SELECT a.*, p.title, p.url, p.image, p.store FROM alerts a "
        "JOIN products p ON p.id=a.product_id ORDER BY a.created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def mark_triggered(alert_id: int) -> None:
    c = _conn()
    c.execute("UPDATE alerts SET triggered_at=?, active=0 WHERE id=?",
              (time.time(), alert_id))
    c.commit()

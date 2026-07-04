"""FastAPI application: REST API + serves the frontend.

Run:  uvicorn app:app --reload --port 8000   (from the backend/ folder)
Open: http://localhost:8000
"""
from __future__ import annotations
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config
import db
import aggregator
import alerts
import scheduler

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="SastaSense", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(config.BASE_DIR), "frontend")


@app.on_event("startup")
def _startup() -> None:
    db.init()
    scheduler.start()


# --------------------------------------------------------------- API models
class AlertIn(BaseModel):
    product_id: int
    kind: str = "price"            # 'price' or 'stock'
    target_price: float | None = None
    email: str = ""


class WatchIn(BaseModel):
    product_id: int


# ------------------------------------------------------------------ routes
@app.get("/api/health")
def health():
    return {"ok": True, "live_scraping": config.LIVE_SCRAPING}


@app.get("/api/search")
def api_search(q: str):
    if not q or len(q.strip()) < 2:
        raise HTTPException(400, "Query too short")
    return aggregator.search(q.strip())


@app.get("/api/product/{product_id}/history")
def api_history(product_id: int):
    p = db.get_product(product_id)
    if not p:
        raise HTTPException(404, "Unknown product")
    hist = db.history(product_id)
    stats = db.price_stats(product_id)
    latest = hist[-1]["price"] if hist else None
    return {
        "product": {"id": p["id"], "title": p["title"], "store": p["store"],
                    "url": p["url"], "image": p["image"]},
        "history": hist,
        "stats": stats,
        "deal": aggregator.deal_score(latest, stats,
                                      hist[-1]["mrp"] if hist else None),
        "alerts": db.alerts_for(product_id),
    }


@app.get("/api/product/{product_id}/refresh")
def api_refresh(product_id: int):
    item = aggregator.refresh_product(product_id)
    if not item:
        raise HTTPException(404, "Could not refresh")
    fired = alerts.check_all()
    return {"item": item, "fired": fired}


# ---- watchlist ----
@app.get("/api/watchlist")
def api_watchlist():
    return [dict(r) for r in db.watchlist()]


@app.post("/api/watchlist")
def api_watch_add(body: WatchIn):
    db.add_to_watchlist(body.product_id)
    return {"ok": True}


@app.delete("/api/watchlist/{product_id}")
def api_watch_remove(product_id: int):
    db.remove_from_watchlist(product_id)
    return {"ok": True}


# ---- alerts ----
@app.get("/api/alerts")
def api_alerts():
    return db.all_alerts_with_product()


@app.post("/api/alerts")
def api_alert_add(body: AlertIn):
    if body.kind == "price" and not body.target_price:
        raise HTTPException(400, "target_price required for price alerts")
    if not db.get_product(body.product_id):
        raise HTTPException(404, "Unknown product")
    db.add_to_watchlist(body.product_id)      # tracking a price implies watching it
    aid = db.add_alert(body.product_id, body.kind, body.target_price, body.email)
    return {"ok": True, "alert_id": aid}


@app.delete("/api/alerts/{alert_id}")
def api_alert_delete(alert_id: int):
    db.delete_alert(alert_id)                 # easy delete -> fixes BuyHatke gripe
    return {"ok": True}


@app.post("/api/alerts/check")
def api_alerts_check():
    return {"fired": alerts.check_all()}


# --------------------------------------------------------- serve frontend
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

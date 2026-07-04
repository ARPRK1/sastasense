# SastaSense 🛍️

**Smart India price-comparison web app** — search a product once and see
live prices across **Amazon.in, Flipkart, Croma and Reliance Digital**, with an
honest "is this a genuine deal?" check, real price-history charts, and reliable
price-drop alerts.

This is the completed, rebuilt version of the `Price_Comparison_Tool` Colab
notebook — turned into a real full web app (BuyHatke-style) and improved based on
researched, real BuyHatke user complaints (see **What we improved** below).

> **Deploy it:** see **[DEPLOY.md](DEPLOY.md)** for one-click Render / Docker / Hugging Face steps.

---

## 🚀 Run it (easiest way)

You need **Python 3.10+** installed. Then:

- **Windows:** double-click **`run.bat`**
- **Mac/Linux:** open a terminal in this folder and run `./run.sh`
  (first time only: `chmod +x run.sh`)

It sets everything up automatically and opens **http://localhost:8000** in your
browser. First run takes a minute to install; after that it's instant.

### Run it manually (if you prefer)
```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --port 8000
```
Then open http://localhost:8000

---

## ✅ Check it works (no internet needed)
```bash
cd backend
python selftest.py
```
This runs the whole pipeline on built-in demo data and prints PASS/FAIL for
search, relevance filtering, price history, deal scoring and alerts.

---

## 🔍 What we improved vs BuyHatke (and why)

Every change below answers a **real, repeatedly-reported** BuyHatke complaint
(researched from MouthShut, Chrome Web Store, Trustpilot and Quora reviews):

| BuyHatke complaint (verified) | What this app does differently |
|---|---|
| **Prices shown are stale / not real-time** | Every price carries a **freshness badge** ("Just updated / Updated recently / May be outdated") and an exact "updated X min ago" timestamp. On-demand re-fetch per product. |
| **Matches wrong / similar products** | A **relevance filter** scores each listing against your search (word coverage + size/capacity units like 128GB), and drops low-confidence junk before you see it. |
| **"Is the discount genuine or an inflated MRP?"** (its most-loved use) | A **Deal Score** compares the current price to the item's *own* history — "Lowest we've seen / Below usual / Around usual / Pricier than usual" — and flags **Inflated MRP** tricks. |
| **Alerts are late / unreliable** | A **background scheduler** refreshes tracked prices and fires alerts deterministically the moment the target is hit. |
| **Can't set multiple target prices per product** | You can add **as many target-price alerts per product as you want** (e.g. notify at ₹4599 *and* ₹4399). |
| **Can't delete alerts (new-UI bug)** | Every alert has an obvious **Delete** button, everywhere it appears. |
| **Cluttered UI / ads / extension glitches** | Clean, fast, **ad-free** single-page UI; best price highlighted; auto dark/light. |

---

## ⚠️ Important note on live scraping (please read)

Amazon.in, Flipkart, etc. **actively block bots**, especially from cloud servers
and data centres. So:

- Live scraping works **best from your own home computer / normal internet**.
- If a site blocks the request or changes its page layout, the app **automatically
  falls back to realistic demo data** so it never shows an empty screen (you'll
  see a small "demo" tag on those results).
- Scrapers occasionally need maintenance when sites change their HTML. Each store
  lives in its own file under `backend/scrapers/` and is easy to update in
  isolation — one broken store never breaks the others.
- To run in **pure demo mode** (great for a portfolio demo), set `LIVE_SCRAPING=false`
  in a `.env` file (copy `backend/.env.example`).

This is an honest limitation of *all* real price-comparison tools, not a bug.

---

## 📧 Optional: email alerts
In-app alerts work out of the box. To also get emails, copy
`backend/.env.example` to `backend/.env` and fill the `SMTP_*` fields
(for Gmail, use an [App Password](https://support.google.com/accounts/answer/185833)).

---

## 🗂️ Project structure
```
deal_aggregator/
├── run.bat / run.sh            # one-click start
├── README.md
├── backend/
│   ├── app.py                  # FastAPI API + serves the frontend
│   ├── aggregator.py           # runs scrapers, ranks results, deal score
│   ├── matcher.py              # relevance filtering + product matching (accuracy)
│   ├── db.py                   # SQLite: products, price history, watchlist, alerts
│   ├── alerts.py               # alert logic + optional email
│   ├── scheduler.py            # background price refresh
│   ├── models.py               # shared Offer data model
│   ├── config.py               # settings (env-driven)
│   ├── selftest.py             # offline end-to-end test
│   ├── requirements.txt
│   └── scrapers/
│       ├── base.py             # shared HTTP + safety wrapper
│       ├── amazon_in.py
│       ├── flipkart.py
│       ├── croma.py
│       ├── reliance_digital.py
│       └── demo.py             # realistic fallback data
└── frontend/
    ├── index.html
    ├── styles.css
    └── app.js
```

## 🛠️ How to add another store
Create `backend/scrapers/yourstore.py` subclassing `BaseScraper`, implement
`search(query) -> list[Offer]`, then register it in the `_LIVE` dict in
`aggregator.py`. That's it — matching, history, deal score and alerts all apply
automatically.

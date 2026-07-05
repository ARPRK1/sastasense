"""Central configuration. Reads from environment (.env supported)."""
import os
from dotenv import load_dotenv

load_dotenv()

# ---- Core paths ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DEAL_DB_PATH", os.path.join(BASE_DIR, "deal_aggregator.db"))

# ---- Scraping behaviour ----
# When True, the app attempts REAL live scraping of the India retail sites.
# When those requests are blocked (very common from cloud servers / datacentres)
# or return nothing, it transparently falls back to the built-in demo provider so
# the app NEVER shows an empty screen. Run from your own machine for best results.
LIVE_SCRAPING = os.getenv("LIVE_SCRAPING", "true").lower() == "true"

# Always keep demo data as a safety net so the UI is never broken.
DEMO_FALLBACK = os.getenv("DEMO_FALLBACK", "true").lower() == "true"

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "8"))
MAX_RESULTS_PER_STORE = int(os.getenv("MAX_RESULTS_PER_STORE", "6"))

# How old (seconds) a cached price may be before we call it "stale".
# This is the core of the "price accuracy / freshness" improvement.
FRESH_SECONDS = int(os.getenv("FRESH_SECONDS", "1800"))      # <=30 min => fresh
STALE_SECONDS = int(os.getenv("STALE_SECONDS", "21600"))     # >6 h     => stale

# ---- Background refresh (keeps tracked prices current for alerts) ----
REFRESH_INTERVAL_MIN = int(os.getenv("REFRESH_INTERVAL_MIN", "60"))

# ---- Optional e-mail alerts (leave blank to use in-app alerts only) ----
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_FROM = os.getenv("ALERT_FROM", SMTP_USER)

# Realistic browser headers - reused by every scraper.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Stores we know how to search. Order = display order.
STORES = ["Amazon.in", "Flipkart", "Croma", "Reliance Digital"]

# ---- Monetisation (affiliate commissions) ----
# Set these as environment variables in Render after signing up (both free).
# AMAZON_ASSOC_TAG: your Amazon Associates tracking id, e.g. "sastasense-21".
#   Appended to every Amazon.in "Buy" link so purchases earn commission.
# CUELINKS_CID: your Cuelinks channel id (cuelinks.com dashboard). A tiny script
#   loads on the site and auto-affiliatizes outbound links to Flipkart, Croma,
#   Reliance, Myntra, Ajio and 1000s more — including programs you can't join
#   directly. This is the one-signup way to monetise every store at once.
AMAZON_ASSOC_TAG = os.getenv("AMAZON_ASSOC_TAG", "")
CUELINKS_CID = os.getenv("CUELINKS_CID", "")

# ---- SEO ----
# Public URL of the site (used in sitemap/robots).
SITE_URL = os.getenv("SITE_URL", "https://sastasense.onrender.com")
# Paste the token Google Search Console gives you (HTML-tag method) here as an
# env var; it's injected into the homepage <head> so you can verify ownership
# WITHOUT a code change.
GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "")

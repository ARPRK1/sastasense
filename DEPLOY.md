# Deploying SastaSense 🚀

You have three easy options. **Render (free)** is the simplest for a public URL.

Everything is already configured — a `Dockerfile`, `render.yaml`, and `Procfile`
are included, and the app reads the host's `$PORT` automatically.

---

## Option A — Render.com (free, recommended)

1. Put this project in a **GitHub repo** (see "Getting it on GitHub" below).
2. Go to **https://render.com** → sign up / log in (free).
3. Click **New +** → **Blueprint**.
4. Connect your GitHub and pick the **sastasense** repo.
5. Render reads `render.yaml`, sets everything up, and clicks **Apply**.
6. Wait for the build (~3–5 min). You get a public URL like
   `https://sastasense.onrender.com`. Done ✅

> Free Render services sleep after inactivity and take ~30s to wake on the first
> visit. That's normal for the free tier.

---

## Option B — Hugging Face Spaces (free, no card, easy uploads)

1. Go to **https://huggingface.co** → sign up / log in.
2. **New Space** → name `sastasense` → **SDK: Docker** → **Blank** → Create.
3. In the Space's **Files** tab, upload this whole project (it already has a
   `Dockerfile`). The Space builds automatically.
4. Your app is live at `https://<your-username>-sastasense.hf.space`. Done ✅

---

## Option C — Anywhere with Docker (VPS, your own PC)

```bash
docker build -t sastasense .
docker run -p 8000:8000 sastasense
```
Open http://localhost:8000

---

## Getting it on GitHub (needed for Option A)

If you have **git** installed:
```bash
cd deal_aggregator
git init
git add .
git commit -m "SastaSense — initial deploy"
# create an empty repo on github.com first, then:
git remote add origin https://github.com/<you>/sastasense.git
git branch -M main
git push -u origin main
```
No git? On **github.com** → **New repository** → after creating it, use
**"uploading an existing file"** and drag the whole `deal_aggregator` folder in.

---

## ⚠️ About live prices in the cloud
Amazon.in / Flipkart block requests from data-centre IPs, so on a cloud host the
app will usually run in **demo mode** (still fully functional — search, charts,
deal score, alerts all work, results just show a "demo" tag). For **real live
prices**, run it on your **home computer** (`run.bat` / `run.sh`) or add a
residential/rotating proxy in `backend/scrapers/base.py`.
This is a limitation of every price-comparison tool, not a bug.

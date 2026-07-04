/* Deal Aggregator frontend logic (vanilla JS, no framework = fast + light). */
const API = ""; // same origin
let chart = null;
let currentProduct = null;

const $ = (s) => document.querySelector(s);
const el = (s) => document.querySelectorAll(s);
const money = (n) => n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN");

// ---------- navigation ----------
el(".navbtn").forEach((b) => b.addEventListener("click", () => {
  el(".navbtn").forEach((x) => x.classList.remove("active"));
  b.classList.add("active");
  const v = b.dataset.view;
  $("#view-search").classList.toggle("hidden", v !== "search");
  $("#view-alerts").classList.toggle("hidden", v !== "alerts");
  if (v === "alerts") loadAlerts();
}));

// ---------- search ----------
$("#searchForm").addEventListener("submit", (e) => { e.preventDefault(); doSearch(); });
el(".chip").forEach((c) => c.addEventListener("click", () => {
  $("#searchInput").value = c.textContent; doSearch();
}));

async function doSearch() {
  const q = $("#searchInput").value.trim();
  if (q.length < 2) return;
  $("#emptyState").classList.add("hidden");
  $("#results").innerHTML = "";
  $("#statusLine").innerHTML = `<span class="spinner"></span> Searching stores for “${q}”…`;
  try {
    const r = await fetch(`${API}/api/search?q=${encodeURIComponent(q)}`);
    if (!r.ok) throw new Error((await r.json()).detail || "Search failed");
    const data = await r.json();
    renderResults(data);
  } catch (err) {
    $("#statusLine").textContent = "⚠️ " + err.message;
  }
}

function renderResults(data) {
  const src = data.using_demo
    ? `Showing <b>demo data</b> (live sites were unreachable from this machine).`
    : `<b>${data.live_results}</b> live results.`;
  $("#statusLine").innerHTML =
    `Found <b>${data.count}</b> matches for “${data.query}”. ${src} ` +
    `Updated ${timeAgo(data.generated_at)}.`;

  if (!data.items.length) {
    $("#results").innerHTML =
      `<p class="muted">No confident matches. Try a simpler search term.</p>`;
    return;
  }
  $("#results").innerHTML = data.items.map(cardHTML).join("");
  el(".card").forEach((c) => c.addEventListener("click", (e) => {
    if (e.target.closest("a") || e.target.closest(".btn-track")) return;
    openProduct(c.dataset.pid, JSON.parse(c.dataset.item));
  }));
  el(".btn-track").forEach((b) => b.addEventListener("click", (e) => {
    e.stopPropagation();
    openProduct(b.dataset.pid, JSON.parse(b.closest(".card").dataset.item));
  }));
}

function cardHTML(i) {
  const deal = i.deal || {};
  const dealBadge = deal.verdict && deal.verdict !== "unknown"
    ? `<span class="badge b-${deal.verdict}">${deal.label}</span>` : "";
  const inflated = deal.inflated_mrp
    ? `<span class="badge b-inflated" title="Big MRP discount but not actually cheap historically">Inflated MRP</span>` : "";
  const fresh = `<span class="badge b-${i.freshness}">${freshLabel(i.freshness)}</span>`;
  const demo = i.source === "demo" ? `<span class="badge b-demo">demo</span>` : "";
  const best = i.is_best_price ? `<span class="badge b-best">Best price</span>` : "";
  const disc = i.discount_pct ? `<span class="disc">${i.discount_pct}% off</span>` : "";
  const mrp = i.mrp && i.mrp > i.price ? `<span class="mrp">${money(i.mrp)}</span>` : "";
  return `
  <div class="card ${i.is_best_price ? "best" : ""}" data-pid="${i.product_id}"
       data-item='${escapeAttr(JSON.stringify(i))}'>
    <div class="card-top">
      <img src="${i.image || ""}" alt="" onerror="this.style.visibility='hidden'"/>
      <div style="flex:1">
        <div class="card-title">${escapeHTML(i.title)}</div>
        <div class="store-row"><span class="store-tag">${i.store}</span>
          ${i.rating ? "★ " + i.rating : ""}</div>
      </div>
    </div>
    <div class="price-row"><span class="price">${money(i.price)}</span> ${mrp} ${disc}</div>
    <div class="badges">${best} ${dealBadge} ${inflated} ${fresh} ${demo}</div>
    <div class="card-actions">
      <a class="btn-buy" href="${i.url}" target="_blank" rel="noopener">Buy</a>
      <button class="btn-track" data-pid="${i.product_id}">Track price</button>
    </div>
  </div>`;
}

// ---------- product / history modal ----------
async function openProduct(pid, item) {
  currentProduct = { pid, item };
  $("#modal").classList.remove("hidden");
  $("#mImg").src = item.image || "";
  $("#mTitle").textContent = item.title;
  $("#mMeta").textContent = `${item.store} • ${money(item.price)}`;
  $("#mDeal").textContent = "Loading price history…";
  $("#mDeal").className = "deal-badge b-typical";
  $("#targetPrice").value = item.price ? Math.round(item.price * 0.9) : "";
  try {
    const r = await fetch(`${API}/api/product/${pid}/history`);
    const data = await r.json();
    drawChart(data.history);
    renderStats(data.stats, item.price);
    const d = data.deal || {};
    $("#mDeal").textContent = d.label || "No history yet";
    $("#mDeal").className = "deal-badge b-" + (d.verdict === "unknown" ? "typical" : d.verdict);
    renderProductAlerts(data.alerts, pid);
  } catch (e) {
    $("#mDeal").textContent = "Could not load history";
  }
}

$("#modalClose").addEventListener("click", () => $("#modal").classList.add("hidden"));
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); });

function drawChart(history) {
  const ctx = $("#historyChart");
  const labels = history.map((h) => new Date(h.ts * 1000).toLocaleDateString("en-IN", { month: "short", day: "numeric" }));
  const prices = history.map((h) => h.price);
  if (chart) chart.destroy();
  if (!history.length) {
    ctx.getContext("2d").clearRect(0, 0, ctx.width, ctx.height);
    return;
  }
  const lowest = Math.min(...prices);
  chart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [{
      label: "Price (₹)", data: prices, tension: .25,
      borderColor: "#5b8cff", backgroundColor: "rgba(91,140,255,.12)",
      fill: true, pointRadius: prices.map((p) => p === lowest ? 5 : 2),
      pointBackgroundColor: prices.map((p) => p === lowest ? "#2ecc71" : "#5b8cff"),
    }]},
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { ticks: { callback: (v) => "₹" + v.toLocaleString("en-IN") } } } },
  });
}

function renderStats(stats, current) {
  const cells = [
    ["Current", money(current)],
    ["Lowest seen", money(stats.lowest)],
    ["Usual (median)", money(stats.median)],
    ["Data points", stats.count || 0],
  ];
  $("#mStats").innerHTML = cells.map(([k, v]) =>
    `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");
}

function renderProductAlerts(alerts, pid) {
  const active = alerts.filter((a) => a.active);
  $("#productAlerts").innerHTML = active.length
    ? active.map((a) => `
      <div class="mini-alert">
        <span>${a.kind === "price" ? "Notify at " + money(a.target_price) : "Notify when in stock"}
          ${a.email ? "→ " + escapeHTML(a.email) : "(in-app)"}</span>
        <button class="alert-del" data-aid="${a.id}">Delete</button>
      </div>`).join("")
    : `<p class="muted" style="font-size:13px">No alerts yet for this product.</p>`;
  el("#productAlerts .alert-del").forEach((b) => b.addEventListener("click", async () => {
    await fetch(`${API}/api/alerts/${b.dataset.aid}`, { method: "DELETE" });
    openProduct(pid, currentProduct.item);
    refreshAlertCount();
  }));
}

$("#addAlertBtn").addEventListener("click", async () => {
  const target = parseFloat($("#targetPrice").value);
  if (!target || target <= 0) return toast("Enter a valid target price");
  const body = { product_id: currentProduct.pid, kind: "price",
    target_price: target, email: $("#alertEmail").value.trim() };
  const r = await fetch(`${API}/api/alerts`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) });
  if (r.ok) {
    toast("Alert set — we'll watch this price for you ✅");
    openProduct(currentProduct.pid, currentProduct.item);
    refreshAlertCount();
  } else { toast("Could not set alert"); }
});

// ---------- alerts view ----------
async function loadAlerts() {
  const list = $("#alertsList");
  list.innerHTML = `<span class="spinner"></span> Loading…`;
  const r = await fetch(`${API}/api/alerts`);
  const alerts = await r.json();
  if (!alerts.length) { list.innerHTML = `<p class="muted">No alerts yet. Search a product and tap “Track price”.</p>`; return; }
  list.innerHTML = alerts.map((a) => `
    <div class="alert-item">
      <img src="${a.image || ""}" onerror="this.style.visibility='hidden'"/>
      <div class="info">
        <div><b>${escapeHTML(a.title)}</b></div>
        <div class="muted" style="font-size:13px">${a.store} •
          ${a.kind === "price" ? "target " + money(a.target_price) : "in-stock alert"}
          <span class="state-tag ${a.active ? "state-active" : "state-fired"}">
            ${a.active ? "watching" : "triggered"}</span></div>
      </div>
      <a class="btn-buy" style="padding:8px 12px;text-decoration:none;border-radius:8px;font-weight:700" href="${a.url}" target="_blank" rel="noopener">Open</a>
      <button class="alert-del" data-aid="${a.id}">Delete</button>
    </div>`).join("");
  el("#alertsList .alert-del").forEach((b) => b.addEventListener("click", async () => {
    await fetch(`${API}/api/alerts/${b.dataset.aid}`, { method: "DELETE" });
    loadAlerts(); refreshAlertCount();
  }));
}

async function refreshAlertCount() {
  try {
    const r = await fetch(`${API}/api/alerts`);
    const a = await r.json();
    const active = a.filter((x) => x.active).length;
    $("#alertCount").textContent = active || "";
  } catch (_) {}
}

// ---------- helpers ----------
function freshLabel(f) { return f === "fresh" ? "Just updated" : f === "recent" ? "Updated recently" : "May be outdated"; }
function timeAgo(ts) {
  const s = Math.max(0, Math.round(Date.now() / 1000 - ts));
  if (s < 60) return "just now";
  if (s < 3600) return Math.round(s / 60) + " min ago";
  return Math.round(s / 3600) + " h ago";
}
function escapeHTML(s) { return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function escapeAttr(s) { return escapeHTML(s).replace(/'/g, "&#39;"); }
let toastTimer;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 2600);
}

// init
refreshAlertCount();
fetch(`${API}/api/health`).then((r) => r.json()).then((h) => {
  $("#footInfo").textContent = h.live_scraping
    ? "Live scraping ON • falls back to demo data if a site blocks the request"
    : "Demo mode • set LIVE_SCRAPING=true to fetch real prices";
}).catch(() => { $("#footInfo").textContent = "Backend not reachable"; });

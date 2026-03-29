// ============================================================
// Knowledge Hub — Frontend
// ============================================================

const API = "";  // same origin

// State
let state = {
  domain: "All",
  source: "all",
  search: "",
  offset: 0,
  limit: 60,
  total: 0,
  viewMode: "grid",   // grid | timeline
  sortOrder: "imported",
};

// ---- Utilities ----

function toast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.getElementById("toasts").appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

const SOURCE_ICONS = {
  youtube: "▶",
  linkedin: "in",
  photo: "📷",
  chatgpt: "💬",
  claude: "✦",
  twitter: "𝕏",
  reddit: "🤖",
  manual: "✏",
};

const SOURCE_LABELS = {
  youtube: "YouTube",
  linkedin: "LinkedIn",
  photo: "Photo",
  chatgpt: "ChatGPT",
  claude: "Claude",
  twitter: "Twitter/X",
  reddit: "Reddit",
  manual: "Manual",
};

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---- View mode ----

function setView(mode) {
  state.viewMode = mode;
  state.offset = 0;
  document.getElementById("btnGrid").classList.toggle("active", mode === "grid");
  document.getElementById("btnTimeline").classList.toggle("active", mode === "timeline");
  const grid = document.getElementById("grid");
  grid.className = mode === "timeline" ? "timeline" : "grid";
  loadItems();
}

function setSort(value) {
  state.sortOrder = value;
  state.offset = 0;
  loadItems();
}

// ---- Render: Grid card ----

function renderCard(item) {
  const icon = SOURCE_ICONS[item.source] || "•";
  const label = SOURCE_LABELS[item.source] || item.source;
  const thumb = item.thumbnail
    ? `<img class="card-thumb" src="${escHtml(item.thumbnail)}" onerror="this.style.display='none'" loading="lazy">`
    : `<div class="card-thumb-placeholder">${icon}</div>`;

  const tags = (item.tags || []).map(t => `<span class="tag">${escHtml(t)}</span>`).join("");
  const summary = item.summary
    ? `<p class="card-summary">${escHtml(item.summary)}</p>`
    : `<p class="card-summary pending">AI summary pending…</p>`;

  const date = item.created_at ? `· ${item.created_at}` : "";

  return `
  <div class="card" data-id="${item.id}" onclick="openItem(${item.id})">
    <div class="card-header">
      ${thumb}
      <div class="card-title">${escHtml(item.title)}</div>
    </div>
    ${item.domain ? `<span class="card-domain">${escHtml(item.domain)}</span>` : ""}
    ${summary}
    ${tags ? `<div class="card-tags">${tags}</div>` : ""}
    <div class="card-footer">
      <span class="card-source src-${item.source}">${escHtml(label)} ${date}</span>
      <div class="card-actions">
        ${item.url ? `<a href="${escHtml(item.url)}" target="_blank" onclick="event.stopPropagation()" class="btn btn-ghost btn-sm">Open ↗</a>` : ""}
        <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteItem(${item.id})">✕</button>
      </div>
    </div>
  </div>`;
}

// ---- Render: Timeline item ----

function renderTimelineItem(item) {
  const icon = SOURCE_ICONS[item.source] || "•";
  const label = SOURCE_LABELS[item.source] || item.source;
  const date = item.created_at || item.imported_at || "";
  const shortDate = date ? date.slice(0, 10) : "—";
  const summary = item.summary || "";
  const tags = (item.tags || []).map(t => `<span class="tag">${escHtml(t)}</span>`).join("");

  return `
  <div class="timeline-item" onclick="openItem(${item.id})">
    <div class="timeline-date">${escHtml(shortDate)}</div>
    <div class="timeline-source-icon src-${item.source}">${icon}</div>
    <div class="timeline-body">
      <div class="timeline-title">${escHtml(item.title)}</div>
      ${summary ? `<div class="timeline-summary">${escHtml(summary.slice(0, 200))}${summary.length > 200 ? "…" : ""}</div>` : ""}
      <div class="timeline-meta">
        ${item.domain ? `<span class="card-domain" style="font-size:10px">${escHtml(item.domain)}</span>` : ""}
        <span style="font-size:11px;color:var(--muted)">${escHtml(label)}</span>
        ${tags ? `<div class="card-tags" style="gap:3px">${tags}</div>` : ""}
        <div class="card-actions" style="opacity:1;gap:4px;margin-left:auto">
          ${item.url ? `<a href="${escHtml(item.url)}" target="_blank" onclick="event.stopPropagation()" class="btn btn-ghost btn-sm">Open ↗</a>` : ""}
          <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteItem(${item.id})">✕</button>
        </div>
      </div>
    </div>
    ${item.thumbnail ? `<img class="timeline-thumb" src="${escHtml(item.thumbnail)}" onerror="this.style.display='none'" loading="lazy">` : ""}
  </div>`;
}

// ---- Load items ----

async function loadItems() {
  const params = new URLSearchParams({
    domain: state.domain,
    source: state.source,
    sort: state.sortOrder,
    limit: state.limit,
    offset: state.offset,
  });
  if (state.search) params.set("search", state.search);

  const grid = document.getElementById("grid");
  grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;color:var(--muted);padding:40px"><span class="spinner"></span> Loading…</div>`;

  try {
    const data = await apiFetch(`/api/items?${params}`);
    state.total = data.total;
    document.getElementById("resultCount").textContent = `${data.total} items`;

    if (data.items.length === 0) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          <div class="icon">🧠</div>
          <h2>No knowledge items yet</h2>
          <p>Click <strong>⬆ Import</strong> above to get started.<br>Import from YouTube playlists, LinkedIn export, photos, ChatGPT, or Claude.</p>
          <br>
          <p style="font-size:12px">Make sure to set your <strong>Anthropic API key</strong> in ⚙ Settings for AI summaries.</p>
        </div>`;
    } else if (state.viewMode === "timeline") {
      grid.innerHTML = data.items.map(renderTimelineItem).join("");
    } else {
      grid.innerHTML = data.items.map(renderCard).join("");
    }
    renderPagination();
  } catch (e) {
    grid.innerHTML = `<div style="grid-column:1/-1;color:var(--danger);padding:20px">Error: ${escHtml(e.message)}</div>`;
  }
}

function renderPagination() {
  const pages = Math.ceil(state.total / state.limit);
  const cur = Math.floor(state.offset / state.limit);
  const pg = document.getElementById("pagination");
  if (pages <= 1) { pg.innerHTML = ""; return; }

  let html = "";
  if (cur > 0) html += `<button class="btn btn-ghost btn-sm" onclick="gotoPage(${cur - 1})">← Prev</button>`;
  html += `<span style="color:var(--muted);font-size:13px">Page ${cur + 1} / ${pages}</span>`;
  if (cur < pages - 1) html += `<button class="btn btn-ghost btn-sm" onclick="gotoPage(${cur + 1})">Next →</button>`;
  pg.innerHTML = html;
}

function gotoPage(n) {
  state.offset = n * state.limit;
  loadItems();
}

// ---- Sidebar ----

async function loadStats() {
  const data = await apiFetch("/api/stats");
  document.getElementById("statTotal").textContent = data.total;
  document.getElementById("statSummarized").textContent = data.summarized;
  document.getElementById("statSources").textContent = Object.keys(data.by_source).length;

  const sourcesEl = document.getElementById("sidebarSources");
  const srcItems = Object.entries(data.by_source)
    .map(([src, cnt]) => `
      <div class="sidebar-item ${state.source === src ? "active" : ""} src-${src}" data-src="${src}">
        <span>${SOURCE_LABELS[src] || src}</span>
        <span class="badge">${cnt}</span>
      </div>`)
    .join("");
  sourcesEl.innerHTML = `
    <div class="sidebar-item ${state.source === "all" ? "active" : ""}" data-src="all">
      <span>All sources</span>
      <span class="badge">${data.total}</span>
    </div>
    ${srcItems}`;
}

async function loadDomains() {
  const data = await apiFetch("/api/domains");
  const el = document.getElementById("sidebarDomains");
  const allDiv = `<div class="sidebar-item ${state.domain === "All" ? "active" : ""}" data-domain="All"><span>All domains</span></div>`;
  const domainDivs = data.map(d => {
    const safe = escHtml(d.domain || "Other");
    return `<div class="sidebar-item ${state.domain === d.domain ? "active" : ""}" data-domain="${safe}">
      <span>${safe}</span><span class="badge">${d.count}</span></div>`;
  }).join("");
  el.innerHTML = allDiv + domainDivs;
}

// Delegated click handlers for sidebar
document.getElementById("sidebarDomains").addEventListener("click", e => {
  const item = e.target.closest("[data-domain]");
  if (item) filterDomain(item.dataset.domain);
});

document.getElementById("sidebarSources").addEventListener("click", e => {
  const item = e.target.closest("[data-src]");
  if (item) filterSource(item.dataset.src);
});

// ---- Filters ----

function filterDomain(domain) {
  state.domain = domain;
  state.offset = 0;
  loadItems();
  loadDomains();
}

function filterSource(source) {
  state.source = source;
  state.offset = 0;
  loadItems();
  loadStats();
  loadDomains();
}

// ---- Settings ----

async function openSettings() {
  const data = await apiFetch("/api/settings");
  document.getElementById("settingAnthropicKey").value = "";
  document.getElementById("settingYoutubeKey").value = data.youtube_api_key || "";
  document.getElementById("settingOpenAIKey").value = "";
  const status = document.getElementById("settingStatus");
  if (data.anthropic_api_key_set) {
    status.style.color = "var(--success)";
    status.textContent = "✓ Anthropic API key is set";
  } else {
    status.style.color = "var(--warning)";
    status.textContent = "⚠ Anthropic API key missing — AI features won't work";
  }
  document.getElementById("settingsModal").classList.remove("hidden");
}

async function saveSettings() {
  const anthropic_api_key = document.getElementById("settingAnthropicKey").value.trim();
  const youtube_api_key = document.getElementById("settingYoutubeKey").value.trim();
  const openai_api_key = document.getElementById("settingOpenAIKey").value.trim();
  const twitter_bearer_token = document.getElementById("settingTwitterToken").value.trim();
  const reddit_client_id = document.getElementById("settingRedditClientId").value.trim();
  const reddit_client_secret = document.getElementById("settingRedditSecret").value.trim();
  try {
    await apiFetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        anthropic_api_key, youtube_api_key, openai_api_key,
        twitter_bearer_token, reddit_client_id, reddit_client_secret,
      }),
    });
    toast("✓ Settings saved", "success");
    document.getElementById("settingsModal").classList.add("hidden");
  } catch (e) {
    toast(e.message, "error");
  }
}

document.getElementById("settingsModal").addEventListener("click", e => {
  if (e.target === document.getElementById("settingsModal"))
    document.getElementById("settingsModal").classList.add("hidden");
});

// ---- Search ----

let searchTimer;
document.getElementById("searchInput").addEventListener("input", e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.search = e.target.value.trim();
    state.offset = 0;
    loadItems();
  }, 350);
});

// ---- Item detail modal ----

async function openItem(id) {
  const item = await apiFetch(`/api/items/${id}`);
  const m = document.getElementById("itemModal");
  document.getElementById("modalTitle").textContent = item.title;
  document.getElementById("modalDomain").textContent = item.domain || "";
  document.getElementById("modalSource").textContent = (SOURCE_LABELS[item.source] || item.source) + (item.created_at ? " · " + item.created_at : "");
  document.getElementById("modalSummary").textContent = item.summary || "No summary yet. Click ✨ AI Summarize to generate one.";
  document.getElementById("modalTags").innerHTML = (item.tags || []).map(t => `<span class="tag">${escHtml(t)}</span>`).join("");
  document.getElementById("modalLink").href = item.url || "#";
  document.getElementById("modalLink").style.display = item.url ? "" : "none";
  document.getElementById("modalContent").textContent = item.content ? item.content.slice(0, 1500) : "";
  document.getElementById("modalThumb").src = item.thumbnail || "";
  document.getElementById("modalThumb").style.display = item.thumbnail ? "" : "none";

  document.getElementById("modalAnalyze").onclick = async () => {
    toast("Running AI analysis…");
    await apiFetch(`/api/items/${id}/summarize`, { method: "POST" });
    toast("AI analysis queued — refresh in a moment", "success");
  };

  m.classList.remove("hidden");
}

document.getElementById("modalClose").addEventListener("click", () => {
  document.getElementById("itemModal").classList.add("hidden");
});
document.getElementById("itemModal").addEventListener("click", e => {
  if (e.target === document.getElementById("itemModal")) {
    document.getElementById("itemModal").classList.add("hidden");
  }
});

// ---- Actions ----

async function analyzeItem(id) {
  await apiFetch(`/api/items/${id}/summarize`, { method: "POST" });
  toast("AI analysis queued", "success");
}

async function deleteItem(id) {
  if (!confirm("Delete this item?")) return;
  await apiFetch(`/api/items/${id}`, { method: "DELETE" });
  toast("Deleted", "success");
  loadItems();
  loadStats();
  loadDomains();
}

async function summarizeAll() {
  const btn = document.getElementById("btnSummarizeAll");
  btn.disabled = true;
  btn.textContent = "⏳ Queuing…";
  try {
    const r = await apiFetch("/api/items/summarize-all", { method: "POST" });
    toast(`AI analysis queued for ${r.queued} items`, "success");
  } catch (e) {
    toast(e.message, "error");
  }
  btn.disabled = false;
  btn.textContent = "✨ AI Summarize All";
}

// ---- Import panel ----

document.getElementById("btnImport").addEventListener("click", () => {
  const panel = document.getElementById("importPanel");
  panel.style.display = panel.style.display === "none" ? "" : "none";
});

// Tab switching
document.querySelectorAll(".import-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".import-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".import-section").forEach(s => s.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`import-${tab.dataset.tab}`).classList.add("active");
  });
});

// Drag & drop helper
function setupDropZone(zoneId, inputId) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  if (!zone || !input) return;  // skip if element doesn't exist
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("dragover");
    input.files = e.dataTransfer.files;
    zone.querySelector(".drop-label").textContent = `${e.dataTransfer.files.length} file(s) selected`;
  });
  input.addEventListener("change", () => {
    if (input.files.length) {
      zone.querySelector(".drop-label").textContent = `${input.files.length} file(s) selected`;
    }
  });
}

setupDropZone("li-drop", "li-file");
setupDropZone("photo-drop", "photo-files");
setupDropZone("gpt-drop", "gpt-file");
setupDropZone("claude-drop", "claude-file");

// ---- YouTube playlist browser ----

let selectedPlaylistId = null;

document.getElementById("btnBrowsePlaylists").addEventListener("click", async () => {
  const channel = document.getElementById("yt-channel").value.trim();
  if (!channel) { toast("Enter a Channel ID or search term first", "error"); return; }

  const btn = document.getElementById("btnBrowsePlaylists");
  btn.disabled = true;
  btn.textContent = "Loading…";

  try {
    const apiKey = document.getElementById("yt-api-key").value.trim();
    const params = new URLSearchParams({ channel });
    if (apiKey) params.set("api_key", apiKey);
    const data = await apiFetch(`/api/youtube/playlists?${params}`);

    const browser = document.getElementById("playlistBrowser");
    const list = document.getElementById("playlistList");

    if (!data.playlists.length) {
      list.innerHTML = `<p style="color:var(--muted);font-size:13px;padding:8px">No playlists found.</p>`;
    } else {
      list.innerHTML = data.playlists.map(pl => `
        <div class="playlist-item" data-id="${escHtml(pl.id)}" onclick="selectPlaylist('${escHtml(pl.id)}', this)">
          ${pl.thumbnail ? `<img src="${escHtml(pl.thumbnail)}" alt="">` : `<div style="width:48px;height:36px;background:var(--surface2);border-radius:4px;flex-shrink:0"></div>`}
          <div class="playlist-item-info">
            <div class="playlist-item-title">${escHtml(pl.title)}</div>
            <div class="playlist-item-meta">${escHtml(pl.channel)}${pl.count ? ` · ${pl.count} videos` : ""}</div>
          </div>
        </div>`).join("");
    }
    browser.style.display = "";
    toast(`Found ${data.playlists.length} playlists`, "success");
  } catch (e) {
    toast(e.message, "error");
  }

  btn.disabled = false;
  btn.textContent = "Browse Playlists";
});

function selectPlaylist(id, el) {
  document.querySelectorAll(".playlist-item").forEach(i => i.classList.remove("selected"));
  el.classList.add("selected");
  selectedPlaylistId = id;
  document.getElementById("yt-playlist-id").value = id;
}

// YouTube import
document.getElementById("yt-form").addEventListener("submit", async e => {
  e.preventDefault();
  const playlist_id = document.getElementById("yt-playlist-id").value.trim();
  const api_key = document.getElementById("yt-api-key").value.trim();
  if (!playlist_id) { toast("Enter or select a Playlist ID", "error"); return; }
  const btn = e.submitter;
  btn.disabled = true; btn.textContent = "Importing…";
  try {
    const r = await apiFetch("/api/import/youtube", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ playlist_id, api_key }),
    });
    toast(`✓ Imported ${r.imported} videos (${r.total} total in playlist)`, "success");
    refresh();
  } catch (e) { toast(e.message, "error"); }
  btn.disabled = false; btn.textContent = "Import Playlist";
});

// LinkedIn import
document.getElementById("li-form").addEventListener("submit", async e => {
  e.preventDefault();
  const file = document.getElementById("li-file").files[0];
  if (!file) { toast("Select a LinkedIn export file", "error"); return; }
  const fd = new FormData(); fd.append("file", file);
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Importing…";
  try {
    const r = await apiFetch("/api/import/linkedin", { method: "POST", body: fd });
    toast(`✓ Imported ${r.imported} LinkedIn items`, "success");
    refresh();
  } catch (e) { toast(e.message, "error"); }
  btn.disabled = false; btn.textContent = "Import";
});

// Photos import
document.getElementById("photo-form").addEventListener("submit", async e => {
  e.preventDefault();
  const files = document.getElementById("photo-files").files;
  if (!files.length) { toast("Select photo files", "error"); return; }
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Uploading…";
  try {
    const r = await apiFetch("/api/import/photos", { method: "POST", body: fd });
    toast(`✓ Uploaded ${r.imported} photos — AI analysis running in background`, "success");
    refresh();
  } catch (e) { toast(e.message, "error"); }
  btn.disabled = false; btn.textContent = "Upload & Analyze";
});

// ChatGPT import
document.getElementById("gpt-form").addEventListener("submit", async e => {
  e.preventDefault();
  const file = document.getElementById("gpt-file").files[0];
  if (!file) { toast("Select your ChatGPT export file", "error"); return; }
  const fd = new FormData(); fd.append("file", file);
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Importing…";
  try {
    const r = await apiFetch("/api/import/chatgpt", { method: "POST", body: fd });
    toast(`✓ Imported ${r.imported} conversations`, "success");
    refresh();
  } catch (e) { toast(e.message, "error"); }
  btn.disabled = false; btn.textContent = "Import";
});

// Claude import
document.getElementById("claude-form").addEventListener("submit", async e => {
  e.preventDefault();
  const file = document.getElementById("claude-file").files[0];
  if (!file) { toast("Select your Claude export file", "error"); return; }
  const fd = new FormData(); fd.append("file", file);
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Importing…";
  try {
    const r = await apiFetch("/api/import/claude", { method: "POST", body: fd });
    toast(`✓ Imported ${r.imported} Claude conversations`, "success");
    refresh();
  } catch (e) { toast(e.message, "error"); }
  btn.disabled = false; btn.textContent = "Import";
});

// Twitter import
document.getElementById("twitter-form").addEventListener("submit", async e => {
  e.preventDefault();
  const username = document.getElementById("tw-username").value.trim();
  const bearer_token = document.getElementById("tw-bearer").value.trim();
  if (!username) { toast("Enter your Twitter username", "error"); return; }
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Importing…";
  try {
    const r = await apiFetch("/api/import/twitter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, bearer_token }),
    });
    toast(`✓ Imported ${r.imported} liked tweets`, "success");
    refresh();
  } catch (e) { toast(e.message, "error"); }
  btn.disabled = false; btn.textContent = "Import Liked Tweets";
});

// Reddit import
document.getElementById("reddit-form").addEventListener("submit", async e => {
  e.preventDefault();
  const username = document.getElementById("reddit-username").value.trim();
  const password = document.getElementById("reddit-password").value.trim();
  if (!username || !password) { toast("Enter Reddit username and password", "error"); return; }
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Importing…";
  try {
    const r = await apiFetch("/api/import/reddit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    toast(`✓ Imported ${r.imported} saved posts`, "success");
    refresh();
  } catch (e) { toast(e.message, "error"); }
  btn.disabled = false; btn.textContent = "Import Saved Posts";
});

// Manual text entry
document.getElementById("manual-form").addEventListener("submit", async e => {
  e.preventDefault();
  const title = document.getElementById("manual-title").value.trim();
  const content = document.getElementById("manual-content").value.trim();
  const url = document.getElementById("manual-url").value.trim();
  if (!title) { toast("Title is required", "error"); return; }
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Adding…";
  try {
    const r = await apiFetch("/api/import/manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content, url }),
    });
    if (r.imported === 0) {
      toast("Item already exists (same title + content)", "info");
    } else {
      toast("✓ Added", "success");
      document.getElementById("manual-title").value = "";
      document.getElementById("manual-content").value = "";
      document.getElementById("manual-url").value = "";
      // Reset filters so the new item is always visible
      state.domain = "All";
      state.source = "all";
      state.offset = 0;
      refresh();
    }
  } catch (e) { toast(e.message, "error"); }
  btn.disabled = false; btn.textContent = "Add & Analyze";
});

// Manual image upload (reuse photo endpoint)
setupDropZone("manual-img-drop", "manual-img-file");
document.getElementById("manual-image-form").addEventListener("submit", async e => {
  e.preventDefault();
  const file = document.getElementById("manual-img-file").files[0];
  if (!file) { toast("Select an image", "error"); return; }
  const fd = new FormData(); fd.append("files", file);
  const btn = e.submitter; btn.disabled = true; btn.textContent = "Uploading…";
  try {
    await apiFetch("/api/import/photos", { method: "POST", body: fd });
    toast("✓ Uploaded", "success");
    state.domain = "All";
    state.source = "all";
    state.offset = 0;
    refresh();
  } catch (e) { toast(e.message, "error"); }
  btn.disabled = false; btn.textContent = "Upload & Analyze";
});

// Manual tab switcher (Text vs Image)
document.querySelectorAll(".manual-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".manual-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    const isText = tab.dataset.mtab === "text";
    document.getElementById("manual-text-section").style.display = isText ? "" : "none";
    document.getElementById("manual-image-section").style.display = isText ? "none" : "";
  });
});

// ---- Auto-refresh ----

function refresh() {
  loadItems();
  loadStats();
  loadDomains();
}

// Poll every 8 seconds while page is visible (picks up background AI results)
setInterval(() => { if (!document.hidden) loadItems(); }, 8000);

// ---- Init ----
refresh();

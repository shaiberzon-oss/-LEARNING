# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Project Is

**Knowledge Hub** — a local web app that aggregates saved content from YouTube, LinkedIn, iPhone Photos, ChatGPT, and Claude conversations, then uses Claude AI to auto-categorize and summarize each item into a personal knowledge base.

---

## How to Run

```bash
# First time — create venv and install deps
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Start the server (run from project root)
cd backend
uvicorn main:app --reload --port 8000
```

Or just double-click `start.bat` (handles everything automatically).

App runs at `http://localhost:8000`.

API key can be set in `.env` (`ANTHROPIC_API_KEY`) **or** entered directly in the UI via the ⚙ Settings button — no file editing required.

---

## Architecture

```
backend/
  main.py          — FastAPI app, all route handlers
  database.py      — sqlite3 helpers: init_db, get_db, insert_item, get/set_setting
  ai.py            — Claude API calls: analyze_text (categorize+summarize), analyze_image (vision)
  connectors/
    youtube.py     — YouTube Data API v3 playlist fetch
    linkedin.py    — LinkedIn export ZIP/CSV/JSON parser
    photos.py      — saves uploaded images to uploads/, returns item dict with _local_path
    chatgpt.py     — OpenAI export ZIP or conversations.json parser
    claude_conv.py — Anthropic export ZIP or JSON parser

frontend/          — vanilla JS SPA served as static files by FastAPI
  index.html
  style.css
  app.js

uploads/           — saved photo files (auto-created)
knowledge.db       — SQLite database (auto-created)
```

**Request flow:**
1. User imports content → connector parses it → `insert_item()` deduplicates by `(source, source_id)` → FastAPI `BackgroundTasks` queues `_ai_analyze_item()` or `_ai_analyze_photo()`
2. AI worker calls `ai.analyze_text()` or `ai.analyze_image()` → updates `domain`, `summary`, `tags` in DB
3. Frontend polls `/api/items` every 8 seconds to pick up new AI results

**Key design decisions:**
- All AI processing is async via `BackgroundTasks` — imports return immediately
- `source_id` deduplication prevents re-importing the same item
- API key priority: env var → DB setting (saved via ⚙ Settings UI)
- Sidebar domain/source filters use `data-domain` / `data-src` attributes + delegated event listeners (not inline `onclick`) to avoid `&` escaping issues in domain names like "Health & Wellness"
- Photos store the file in `uploads/`, only the relative path goes into the DB

**Database schema (SQLite):**
```sql
items(id, source, source_id, title, content, url, thumbnail, summary, domain, tags, created_at, imported_at)
settings(key, value)
```

---

## Adding a New Source Connector

1. Create `backend/connectors/mysource.py` with a `parse_export(bytes, filename) -> list[dict]` function returning item dicts with keys: `source`, `source_id`, `title`, `content`, `url`, `thumbnail`, `created_at`
2. Add an import endpoint in `main.py` following the same pattern as the existing ones
3. Add an import tab in `frontend/index.html` and the form submit handler in `frontend/app.js`
4. Add the source label/icon to `SOURCE_LABELS` / `SOURCE_ICONS` in `app.js`

---

## Auto-Documentation Rule

**Always update this file** when adding, editing, or removing files:
- Add new files to the Project Structure table below
- Log changes in the Changelog

---

## Project Structure

| File | Description | Last Changed |
|---|---|---|
| `CLAUDE.MD` | This file | 2026-03-08 (update 2) |
| `requirements.txt` | Python dependencies | 2026-03-08 |
| `.env.example` | Example env vars | 2026-03-08 |
| `start.bat` | Windows startup script | 2026-03-08 |
| `backend/main.py` | FastAPI app — all API endpoints | 2026-03-08 |
| `backend/database.py` | SQLite init, CRUD helpers | 2026-03-08 |
| `backend/ai.py` | Claude API — text + vision analysis | 2026-03-08 |
| `backend/connectors/youtube.py` | YouTube Data API v3 | 2026-03-08 |
| `backend/connectors/linkedin.py` | LinkedIn export parser | 2026-03-08 |
| `backend/connectors/photos.py` | Photo upload handler | 2026-03-08 |
| `backend/connectors/chatgpt.py` | ChatGPT export parser | 2026-03-08 |
| `backend/connectors/claude_conv.py` | Claude export parser | 2026-03-08 |
| `backend/connectors/twitter.py` | Twitter/X liked tweets via API v2 | 2026-03-08 |
| `backend/connectors/reddit.py` | Reddit saved posts via OAuth API | 2026-03-08 |
| `frontend/index.html` | SPA HTML | 2026-03-08 |
| `frontend/style.css` | Dark-theme CSS | 2026-03-08 |
| `frontend/app.js` | Frontend JS | 2026-03-08 |

---

## Changelog

### 2026-03-08 (update 2)
- Fixed critical JS bug: `setupDropZone("yt-drop",...)` called on non-existent element, crashing all import form handlers — added null guard
- Dynamic AI domains: removed hardcoded DOMAINS list in `ai.py`, Claude now freely determines best category per item
- Timeline view: added Grid/Timeline toggle + sort (Recently imported / Newest first / Oldest first)
- YouTube playlist browser: new `/api/youtube/playlists` endpoint + UI to browse channel playlists and pick one to import
- Settings: added OpenAI API key field (stored in DB, future use for GPT-based analysis)
- Improved onboarding instructions in all import tabs (step-by-step per platform)
- `filterSource()` now also refreshes domain sidebar
- `deleteItem()` also refreshes domain sidebar

### 2026-03-08
- Initialized project — full build from scratch
- FastAPI backend, SQLite DB, 5 source connectors, Claude API integration
- Web UI: dark theme, domain sidebar, import panel, item cards, settings modal
- Fixed domain sidebar filter (delegated events, `data-domain` attrs)
- Added ⚙ Settings modal — API key can be entered in UI, saved to DB
- Added API key fallback: env var → DB setting

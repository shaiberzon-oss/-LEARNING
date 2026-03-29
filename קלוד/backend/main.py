"""Knowledge Hub — FastAPI backend."""
import os
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import database as db
import ai
from connectors import youtube, linkedin, photos, chatgpt, claude_conv, twitter, reddit

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Knowledge Hub")
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


@app.on_event("startup")
def startup():
    db.init_db()


# Serve uploaded photos
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Serve frontend static assets (CSS, JS)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ---------------------------------------------------------------------------
# Helper — background AI analysis
# ---------------------------------------------------------------------------

def _ai_analyze_item(item_id: int):
    """Run in background: categorize + summarize a single item."""
    conn = db.get_db()
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not row:
        conn.close()
        return
    row = db.item_to_dict(row)
    try:
        result = ai.analyze_text(row["title"], row["content"])
        conn.execute(
            "UPDATE items SET domain=?, summary=?, tags=? WHERE id=?",
            (result.get("domain", "Other"), result.get("summary", ""),
             json.dumps(result.get("tags", [])), item_id)
        )
        conn.commit()
    except Exception as e:
        print(f"AI error for item {item_id}: {e}")
    finally:
        conn.close()


def _ai_analyze_photo(item_id: int, local_path: str):
    """Run in background: vision-analyze a photo."""
    conn = db.get_db()
    try:
        result = ai.analyze_image(local_path)
        conn.execute(
            "UPDATE items SET title=?, domain=?, summary=?, tags=?, content=? WHERE id=?",
            (
                result.get("title", "Photo"),
                result.get("domain", "Other"),
                result.get("summary", ""),
                json.dumps(result.get("tags", [])),
                result.get("extracted_text", ""),
                item_id,
            )
        )
        conn.commit()
    except Exception as e:
        print(f"Photo AI error for item {item_id}: {e}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

@app.get("/api/items")
def get_items(
    domain: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("imported", pattern="^(imported|newest|oldest)$"),
    limit: int = Query(60, le=200),
    offset: int = 0,
):
    conn = db.get_db()
    where, params = [], []

    if domain and domain != "All":
        where.append("domain=?")
        params.append(domain)
    if source and source != "all":
        where.append("source=?")
        params.append(source)
    if search:
        where.append("(title LIKE ? OR summary LIKE ? OR content LIKE ? OR tags LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like, like])

    order = {
        "newest": "COALESCE(created_at, imported_at) DESC",
        "oldest": "COALESCE(created_at, imported_at) ASC",
        "imported": "imported_at DESC",
    }.get(sort, "imported_at DESC")

    sql = "SELECT * FROM items"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    total_sql = "SELECT COUNT(*) FROM items"
    if where:
        total_sql += " WHERE " + " AND ".join(where[:-0])
    total = conn.execute(
        "SELECT COUNT(*) FROM items" + (" WHERE " + " AND ".join(where) if where else ""),
        params[:-2],
    ).fetchone()[0]
    conn.close()
    return {"items": [db.item_to_dict(r) for r in rows], "total": total}


@app.get("/api/items/{item_id}")
def get_item(item_id: int):
    conn = db.get_db()
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Item not found")
    return db.item_to_dict(row)


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int):
    conn = db.get_db()
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/items/{item_id}/summarize")
def summarize_item(item_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(_ai_analyze_item, item_id)
    return {"ok": True, "message": "AI analysis started"}


@app.post("/api/items/summarize-all")
def summarize_all(background_tasks: BackgroundTasks):
    conn = db.get_db()
    rows = conn.execute(
        "SELECT id FROM items WHERE (summary='' OR summary IS NULL) AND source != 'photo'"
    ).fetchall()
    conn.close()
    for row in rows:
        background_tasks.add_task(_ai_analyze_item, row["id"])
    return {"ok": True, "queued": len(rows)}


# ---------------------------------------------------------------------------
# Stats & domains
# ---------------------------------------------------------------------------

@app.get("/api/stats")
def get_stats():
    conn = db.get_db()
    total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    summarized = conn.execute(
        "SELECT COUNT(*) FROM items WHERE summary != '' AND summary IS NOT NULL"
    ).fetchone()[0]
    by_source = {
        r["source"]: r["cnt"]
        for r in conn.execute("SELECT source, COUNT(*) as cnt FROM items GROUP BY source").fetchall()
    }
    conn.close()
    return {"total": total, "summarized": summarized, "by_source": by_source}


@app.get("/api/domains")
def get_domains():
    conn = db.get_db()
    rows = conn.execute(
        "SELECT domain, COUNT(*) as cnt FROM items GROUP BY domain ORDER BY cnt DESC"
    ).fetchall()
    conn.close()
    return [{"domain": r["domain"], "count": r["cnt"]} for r in rows]


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------

class YouTubeRequest(BaseModel):
    playlist_id: str
    api_key: Optional[str] = None


@app.post("/api/import/youtube")
def import_youtube(req: YouTubeRequest, background_tasks: BackgroundTasks):
    api_key = req.api_key or os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        raise HTTPException(400, "YouTube API key not set. Add YOUTUBE_API_KEY to .env or provide it in the request.")
    try:
        playlist_items = youtube.fetch_playlist(req.playlist_id, api_key)
    except Exception as e:
        raise HTTPException(400, f"YouTube API error: {e}")

    conn = db.get_db()
    added = 0
    for item in playlist_items:
        new_id = db.insert_item(conn, item)
        if new_id:
            added += 1
            background_tasks.add_task(_ai_analyze_item, new_id)
    conn.commit()
    conn.close()
    return {"ok": True, "imported": added, "total": len(playlist_items)}


# ---------------------------------------------------------------------------
# LinkedIn
# ---------------------------------------------------------------------------

@app.post("/api/import/linkedin")
async def import_linkedin_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    data = await file.read()
    items = linkedin.parse_export(data, file.filename or "export.zip")
    if not items:
        raise HTTPException(400, "No items found in the LinkedIn export. See import instructions.")

    conn = db.get_db()
    added = 0
    for item in items:
        new_id = db.insert_item(conn, item)
        if new_id:
            added += 1
            background_tasks.add_task(_ai_analyze_item, new_id)
    conn.commit()
    conn.close()
    return {"ok": True, "imported": added, "total": len(items)}


# ---------------------------------------------------------------------------
# Photos
# ---------------------------------------------------------------------------

@app.post("/api/import/photos")
async def import_photos(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    conn = db.get_db()
    added = 0
    for upload in files:
        data = await upload.read()
        item = photos.save_photo(data, upload.filename or "photo.jpg")
        if not item:
            continue
        local_path = item.pop("_local_path")
        new_id = db.insert_item(conn, item)
        if new_id:
            added += 1
            background_tasks.add_task(_ai_analyze_photo, new_id, local_path)
    conn.commit()
    conn.close()
    return {"ok": True, "imported": added}


# ---------------------------------------------------------------------------
# ChatGPT
# ---------------------------------------------------------------------------

@app.post("/api/import/chatgpt")
async def import_chatgpt_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    data = await file.read()
    items = chatgpt.parse_export(data, file.filename or "conversations.json")
    if not items:
        raise HTTPException(400, "No conversations found in the ChatGPT export.")

    conn = db.get_db()
    added = 0
    for item in items:
        new_id = db.insert_item(conn, item)
        if new_id:
            added += 1
            background_tasks.add_task(_ai_analyze_item, new_id)
    conn.commit()
    conn.close()
    return {"ok": True, "imported": added, "total": len(items)}


# ---------------------------------------------------------------------------
# Claude conversations
# ---------------------------------------------------------------------------

@app.post("/api/import/claude")
async def import_claude_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    data = await file.read()
    items = claude_conv.parse_export(data, file.filename or "conversations.json")
    if not items:
        raise HTTPException(400, "No conversations found in the Claude export.")

    conn = db.get_db()
    added = 0
    for item in items:
        new_id = db.insert_item(conn, item)
        if new_id:
            added += 1
            background_tasks.add_task(_ai_analyze_item, new_id)
    conn.commit()
    conn.close()
    return {"ok": True, "imported": added, "total": len(items)}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Twitter/X
# ---------------------------------------------------------------------------

class TwitterRequest(BaseModel):
    username: str
    bearer_token: Optional[str] = None
    max_items: int = 200


@app.post("/api/import/twitter")
def import_twitter(req: TwitterRequest, background_tasks: BackgroundTasks):
    token = req.bearer_token or db.get_setting("twitter_bearer_token", "")
    if not token:
        raise HTTPException(400, "Twitter Bearer Token not set. Add it in Settings ⚙.")
    try:
        items = twitter.fetch_liked_tweets(req.username, token, max_items=req.max_items)
    except Exception as e:
        raise HTTPException(400, f"Twitter API error: {e}")

    conn = db.get_db()
    added = 0
    for item in items:
        new_id = db.insert_item(conn, item)
        if new_id:
            added += 1
            background_tasks.add_task(_ai_analyze_item, new_id)
    conn.commit()
    conn.close()
    return {"ok": True, "imported": added, "total": len(items)}


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------

class RedditRequest(BaseModel):
    username: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    password: str
    max_items: int = 200


@app.post("/api/import/reddit")
def import_reddit(req: RedditRequest, background_tasks: BackgroundTasks):
    cid = req.client_id or db.get_setting("reddit_client_id", "")
    csecret = req.client_secret or db.get_setting("reddit_client_secret", "")
    if not cid or not csecret:
        raise HTTPException(400, "Reddit client_id and client_secret not set. Add them in Settings ⚙.")
    try:
        items = reddit.fetch_saved_posts(
            req.username, cid, csecret, req.password, max_items=req.max_items
        )
    except Exception as e:
        raise HTTPException(400, f"Reddit API error: {e}")

    conn = db.get_db()
    added = 0
    for item in items:
        new_id = db.insert_item(conn, item)
        if new_id:
            added += 1
            background_tasks.add_task(_ai_analyze_item, new_id)
    conn.commit()
    conn.close()
    return {"ok": True, "imported": added, "total": len(items)}


# ---------------------------------------------------------------------------
# Manual entry
# ---------------------------------------------------------------------------

class ManualItemBody(BaseModel):
    title: str
    content: Optional[str] = ""
    url: Optional[str] = ""


@app.post("/api/import/manual")
def import_manual(body: ManualItemBody, background_tasks: BackgroundTasks):
    if not body.title.strip():
        raise HTTPException(400, "Title is required.")
    import hashlib
    sid = hashlib.md5(f"{body.title}{body.content}".encode()).hexdigest()[:12]
    item = {
        "source": "manual",
        "source_id": f"manual_{sid}",
        "title": body.title.strip(),
        "content": (body.content or "").strip(),
        "url": (body.url or "").strip(),
        "thumbnail": "",
        "created_at": "",
    }
    conn = db.get_db()
    new_id = db.insert_item(conn, item)
    if new_id:
        background_tasks.add_task(_ai_analyze_item, new_id)
    conn.commit()
    conn.close()
    return {"ok": True, "imported": 1 if new_id else 0}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@app.get("/api/settings")
def get_settings():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip() or db.get_setting("anthropic_api_key", "")
    youtube_key = os.getenv("YOUTUBE_API_KEY", "").strip() or db.get_setting("youtube_api_key", "")
    return {
        "anthropic_api_key_set": bool(anthropic_key),
        "youtube_api_key": youtube_key,
        "twitter_bearer_token_set": bool(db.get_setting("twitter_bearer_token", "")),
        "reddit_client_id": db.get_setting("reddit_client_id", ""),
    }


class SettingsBody(BaseModel):
    anthropic_api_key: Optional[str] = None
    youtube_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    twitter_bearer_token: Optional[str] = None
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None


@app.post("/api/settings")
def update_settings(body: SettingsBody):
    if body.anthropic_api_key is not None:
        db.set_setting("anthropic_api_key", body.anthropic_api_key.strip())
    if body.youtube_api_key is not None:
        db.set_setting("youtube_api_key", body.youtube_api_key.strip())
    if body.openai_api_key is not None:
        db.set_setting("openai_api_key", body.openai_api_key.strip())
    if body.twitter_bearer_token is not None:
        db.set_setting("twitter_bearer_token", body.twitter_bearer_token.strip())
    if body.reddit_client_id is not None:
        db.set_setting("reddit_client_id", body.reddit_client_id.strip())
    if body.reddit_client_secret is not None:
        db.set_setting("reddit_client_secret", body.reddit_client_secret.strip())
    return {"ok": True}


# ---------------------------------------------------------------------------
# YouTube playlist browser
# ---------------------------------------------------------------------------

@app.get("/api/youtube/playlists")
def get_youtube_playlists(channel: str, api_key: Optional[str] = None):
    key = api_key or os.getenv("YOUTUBE_API_KEY", "") or db.get_setting("youtube_api_key", "")
    if not key:
        raise HTTPException(400, "YouTube API key not set. Add it in Settings ⚙.")
    try:
        from connectors.youtube import list_channel_playlists
        playlists = list_channel_playlists(channel, key)
        return {"playlists": playlists}
    except Exception as e:
        raise HTTPException(400, f"YouTube API error: {e}")

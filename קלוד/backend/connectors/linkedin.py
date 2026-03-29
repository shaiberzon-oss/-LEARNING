"""LinkedIn connector — parses LinkedIn data export ZIP or CSV files."""
import zipfile
import csv
import io
import json
from pathlib import Path


def parse_export(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Parse a LinkedIn data export.

    Accepts:
    - A ZIP file from LinkedIn's 'Download your data' feature
    - A single CSV file
    - A JSON file with an array of objects containing title/url/content fields
    """
    fname = filename.lower()

    if fname.endswith(".zip"):
        return _parse_zip(file_bytes)
    elif fname.endswith(".csv"):
        return _parse_csv(io.StringIO(file_bytes.decode("utf-8", errors="replace")))
    elif fname.endswith(".json"):
        return _parse_json(file_bytes)
    else:
        return []


def _parse_zip(data: bytes) -> list[dict]:
    items = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            lower = name.lower()
            # LinkedIn export files that contain useful content
            if any(k in lower for k in ("saved", "article", "share", "post", "content")):
                with zf.open(name) as f:
                    content = f.read()
                    if lower.endswith(".csv"):
                        items.extend(_parse_csv(io.StringIO(content.decode("utf-8", errors="replace"))))
                    elif lower.endswith(".json"):
                        items.extend(_parse_json(content))
    return items


def _parse_csv(stream) -> list[dict]:
    items = []
    try:
        reader = csv.DictReader(stream)
        for row in reader:
            # Normalize column names to lowercase
            row = {k.lower().strip(): v for k, v in row.items()}

            title = (
                row.get("title") or row.get("name") or row.get("headline")
                or row.get("company name") or row.get("position title") or "LinkedIn Item"
            )
            url = row.get("url") or row.get("link") or row.get("profile url") or ""
            content_parts = []
            for key in ("description", "notes", "summary", "snippet", "content", "text"):
                val = row.get(key, "").strip()
                if val:
                    content_parts.append(val)

            date = row.get("date") or row.get("saved at") or row.get("created at") or ""

            items.append({
                "source": "linkedin",
                "source_id": f"li_{hash(title + url) & 0xFFFFFFFF}",
                "title": str(title).strip() or "LinkedIn Item",
                "content": " | ".join(content_parts),
                "url": str(url).strip(),
                "thumbnail": "",
                "created_at": str(date)[:10],
            })
    except Exception:
        pass
    return items


def _parse_json(data: bytes) -> list[dict]:
    items = []
    try:
        records = json.loads(data)
        if isinstance(records, dict):
            records = [records]
        for r in records:
            if not isinstance(r, dict):
                continue
            title = r.get("title") or r.get("name") or r.get("headline") or "LinkedIn Item"
            url = r.get("url") or r.get("link") or ""
            content = r.get("content") or r.get("description") or r.get("text") or ""
            date = r.get("date") or r.get("created_at") or ""
            items.append({
                "source": "linkedin",
                "source_id": f"li_{hash(title + url) & 0xFFFFFFFF}",
                "title": str(title).strip(),
                "content": str(content).strip(),
                "url": str(url).strip(),
                "thumbnail": "",
                "created_at": str(date)[:10],
            })
    except Exception:
        pass
    return items

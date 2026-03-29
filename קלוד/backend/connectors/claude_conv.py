"""Claude connector — parses Anthropic conversation exports (ZIP or JSON)."""
import zipfile
import json
import io
from datetime import datetime


def parse_export(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Accept:
    - A ZIP file from Anthropic's export feature
    - A JSON file with an array of conversations
    """
    fname = filename.lower()
    if fname.endswith(".zip"):
        return _parse_zip(file_bytes)
    elif fname.endswith(".json"):
        return _parse_json(file_bytes)
    return []


def _parse_zip(data: bytes) -> list[dict]:
    items = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            lower = name.lower()
            if lower.endswith(".json"):
                with zf.open(name) as f:
                    items.extend(_parse_json(f.read()))
    return items


def _parse_json(data: bytes) -> list[dict]:
    items = []
    try:
        payload = json.loads(data)
    except Exception:
        return []

    # Handle both a list of convos or a single convo
    conversations = payload if isinstance(payload, list) else [payload]

    for convo in conversations:
        if not isinstance(convo, dict):
            continue

        convo_id = convo.get("uuid") or convo.get("id") or ""
        title = convo.get("name") or convo.get("title") or "Claude Conversation"

        # Parse date
        raw_date = convo.get("created_at") or convo.get("create_time") or ""
        date = ""
        if raw_date:
            try:
                date = str(raw_date)[:10]
            except Exception:
                pass

        # Extract messages — Anthropic format: chat_messages list
        messages = []
        for msg in convo.get("chat_messages", convo.get("messages", [])):
            if not isinstance(msg, dict):
                continue
            sender = msg.get("sender") or msg.get("role") or ""
            # Content can be a string or a list of content blocks
            raw = msg.get("text") or msg.get("content") or ""
            if isinstance(raw, list):
                text = " ".join(
                    block.get("text", "") for block in raw
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            else:
                text = str(raw)

            text = text.strip()
            if text:
                label = "HUMAN" if sender in ("human", "user") else "CLAUDE"
                messages.append(f"[{label}]: {text}")

        full_text = "\n\n".join(messages[:30])

        items.append({
            "source": "claude",
            "source_id": f"claude_{convo_id or (hash(title) & 0xFFFFFFFF)}",
            "title": str(title).strip(),
            "content": full_text,
            "url": "",
            "thumbnail": "",
            "created_at": date,
        })

    return items

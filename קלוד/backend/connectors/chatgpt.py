"""ChatGPT connector — parses OpenAI data export (conversations.json or ZIP)."""
import zipfile
import json
import io
from datetime import datetime


def parse_export(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Accept:
    - A ZIP file from OpenAI's 'Export data' feature (contains conversations.json)
    - The conversations.json file directly
    """
    fname = filename.lower()
    if fname.endswith(".zip"):
        return _parse_zip(file_bytes)
    elif fname.endswith(".json"):
        return _parse_conversations_json(file_bytes)
    return []


def _parse_zip(data: bytes) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if name.lower() == "conversations.json" or name.lower().endswith("/conversations.json"):
                with zf.open(name) as f:
                    return _parse_conversations_json(f.read())
    return []


def _parse_conversations_json(data: bytes) -> list[dict]:
    items = []
    try:
        conversations = json.loads(data)
    except Exception:
        return []

    for convo in conversations:
        if not isinstance(convo, dict):
            continue

        title = convo.get("title") or "ChatGPT Conversation"
        create_time = convo.get("create_time") or convo.get("update_time")
        date = ""
        if create_time:
            try:
                date = datetime.fromtimestamp(float(create_time)).strftime("%Y-%m-%d")
            except Exception:
                pass

        # Extract messages from the mapping structure
        messages = []
        mapping = convo.get("mapping", {})
        if mapping:
            for node in mapping.values():
                msg = node.get("message")
                if not msg:
                    continue
                role = msg.get("author", {}).get("role", "")
                content_obj = msg.get("content", {})
                parts = content_obj.get("parts", []) if isinstance(content_obj, dict) else []
                text = " ".join(str(p) for p in parts if isinstance(p, str) and p.strip())
                if text and role in ("user", "assistant"):
                    messages.append(f"[{role.upper()}]: {text}")
        elif convo.get("messages"):
            # Some exports use a flat messages list
            for m in convo["messages"]:
                role = m.get("role", m.get("author", ""))
                text = m.get("content", m.get("text", ""))
                if text:
                    messages.append(f"[{role.upper()}]: {text}")

        full_text = "\n\n".join(messages[:30])  # cap at 30 messages to keep content manageable

        items.append({
            "source": "chatgpt",
            "source_id": f"gpt_{convo.get('id', hash(title) & 0xFFFFFFFF)}",
            "title": str(title).strip(),
            "content": full_text,
            "url": "",
            "thumbnail": "",
            "created_at": date,
        })

    return items

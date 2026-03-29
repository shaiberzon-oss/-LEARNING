import os
import json
import base64
import anthropic
from pathlib import Path


def get_client() -> anthropic.Anthropic:
    # Priority: env var → database setting
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        from database import get_setting
        api_key = get_setting("anthropic_api_key", "").strip()
    if not api_key:
        raise ValueError("Anthropic API key not set. Add it in Settings ⚙ inside the app.")
    return anthropic.Anthropic(api_key=api_key)


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


def analyze_text(title: str, content: str = "") -> dict:
    """Categorize and summarize a text-based knowledge item."""
    client = get_client()
    body = f"Title: {title}"
    if content:
        body += f"\n\nContent:\n{content[:3000]}"

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": (
                f"Analyze this knowledge item and respond ONLY with valid JSON.\n\n"
                f"{body}\n\n"
                f"Create an appropriate domain/category name based on the actual content "
                f"(be specific, e.g. 'AI & Machine Learning', 'Productivity', 'Nutrition', "
                f"'Entrepreneurship', 'Python Programming', 'Mental Health', 'Investing', etc.).\n"
                f"Format:\n"
                f'{{"domain":"...","summary":"2-3 sentence summary of key insights","tags":["tag1","tag2","tag3"]}}'
            ),
        }],
    )
    try:
        return _parse_json_response(response.content[0].text)
    except Exception:
        return {"domain": "Other", "summary": f"Content about: {title}", "tags": []}


def analyze_image(image_path: str) -> dict:
    """Use Claude vision to analyze a photo and extract knowledge."""
    client = get_client()

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = Path(image_path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "image/jpeg")

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_data},
                },
                {
                    "type": "text",
                    "text": (
                        f"Analyze this image as a knowledge item. Respond ONLY with valid JSON.\n\n"
                        f"If it is a screenshot of text/article: extract the key information.\n"
                        f"If it is a photo: describe what knowledge or insight it represents.\n\n"
                        f"Create an appropriate domain/category name based on the actual content.\n\n"
                        f"Format:\n"
                        f'{{"title":"descriptive title","domain":"...","summary":"2-3 sentences of key insights",'
                        f'"tags":["tag1","tag2","tag3"],"extracted_text":"text from screenshot or empty string"}}'
                    ),
                },
            ],
        }],
    )
    try:
        return _parse_json_response(response.content[0].text)
    except Exception:
        return {
            "title": Path(image_path).stem,
            "domain": "Other",
            "summary": "An image from your knowledge collection.",
            "tags": [],
            "extracted_text": "",
        }

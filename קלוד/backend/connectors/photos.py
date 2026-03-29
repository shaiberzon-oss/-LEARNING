"""Photos connector — saves uploaded images and returns item dicts for AI analysis."""
import shutil
import uuid
from pathlib import Path

UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def save_photo(file_bytes: bytes, original_filename: str) -> dict | None:
    """
    Save an uploaded photo to the uploads directory.
    Returns a partial item dict (without AI fields; those come later).
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        return None

    UPLOADS_DIR.mkdir(exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOADS_DIR / unique_name
    dest.write_bytes(file_bytes)

    return {
        "source": "photo",
        "source_id": f"photo_{unique_name}",
        "title": Path(original_filename).stem.replace("_", " ").replace("-", " ").title(),
        "content": "",
        "url": f"/uploads/{unique_name}",
        "thumbnail": f"/uploads/{unique_name}",
        "created_at": "",
        "_local_path": str(dest),  # used by AI connector, stripped before DB insert
    }

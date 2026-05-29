"""Uploaded file storage for future binary formats (PDF, Word, etc.)."""

import os

from backend.storage import base as storage_base


def save_uploaded_file(layer_id: str, filename: str, content: bytes) -> str:
    safe_name = os.path.basename(filename)
    dest_dir = os.path.join(storage_base.FILES_DIR, layer_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, safe_name)
    with open(dest_path, "wb") as f:
        f.write(content)
    return dest_path


def get_file_path(file_path: str) -> str | None:
    if os.path.exists(file_path):
        return file_path
    return None

"""Knowledge base CRUD (global relation_objects + relations)."""

import json
import os

from backend.storage.base import _lock
from backend.storage import base as storage_base


def get_knowledge() -> dict:
    with _lock:
        if not os.path.exists(storage_base.KNOWLEDGE_PATH):
            return {"relation_objects": [], "relations": []}
        with open(storage_base.KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)


def save_knowledge(data: dict):
    with _lock:
        with open(storage_base.KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

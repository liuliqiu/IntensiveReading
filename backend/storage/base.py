"""Storage base: paths, lock, id/time utilities, raw JSON read/write."""

import json
import os
import uuid
import threading
from datetime import datetime, timezone

from backend.config import DATA_DIR, LAYERS_DIR, FILES_DIR, KNOWLEDGE_PATH

_lock = threading.RLock()


def gen_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Document raw I/O ──

def _doc_path(doc_id: str) -> str:
    return os.path.join(DATA_DIR, f"{doc_id}.json")


def _read_doc(doc_id: str) -> dict | None:
    path = _doc_path(doc_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_doc(data: dict):
    path = _doc_path(data["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Layer raw I/O ──

def _layer_path(layer_id: str) -> str:
    return os.path.join(LAYERS_DIR, f"{layer_id}.json")


def _read_layer(layer_id: str) -> dict | None:
    path = _layer_path(layer_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_layer(data: dict):
    path = _layer_path(data["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

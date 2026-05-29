"""Document CRUD + token operations."""

import os

from backend.storage import base as storage_base
from backend.storage.base import gen_id, utcnow, _lock, _read_doc, _write_doc


def get_document(doc_id: str) -> dict | None:
    with _lock:
        return _read_doc(doc_id)


def list_documents() -> list[dict]:
    with _lock:
        docs = []
        if not os.path.exists(storage_base.DATA_DIR):
            return docs
        for filename in sorted(os.listdir(storage_base.DATA_DIR)):
            if filename.endswith(".json"):
                doc_id = filename[:-5]
                data = _read_doc(doc_id)
                if data:
                    docs.append(data)
        docs.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
        return docs


def save_document(data: dict):
    with _lock:
        _write_doc(data)


def split_token(doc_id: str, token_id: str, offsets_to_move: list[int]) -> dict | None:
    with _lock:
        doc = _read_doc(doc_id)
        if not doc:
            return None
        target = None
        for t in doc["tokens"]:
            if t["id"] == token_id:
                target = t
                break
        if not target:
            return None
        if len(target["start_offsets"]) <= 1:
            return None

        move_set = set(offsets_to_move)
        remaining = [o for o in target["start_offsets"] if o not in move_set]
        moved = [o for o in target["start_offsets"] if o in move_set]

        if not remaining or not moved:
            return None

        target["start_offsets"] = sorted(remaining)
        new_token = {
            "id": gen_id(),
            "text": target["text"],
            "start_offsets": sorted(moved),
            "style_type": "default",
        }
        insert_idx = doc["tokens"].index(target) + 1
        doc["tokens"].insert(insert_idx, new_token)

        doc["updated_at"] = utcnow()
        _write_doc(doc)
        return doc


def find_token_doc_id(token_id: str) -> str | None:
    with _lock:
        for doc in list_documents():
            for t in doc.get("tokens", []):
                if t["id"] == token_id:
                    return doc["id"]
        return None

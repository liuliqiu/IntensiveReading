import json
import os
import uuid
import threading
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "documents")

_lock = threading.RLock()


def init():
    os.makedirs(DATA_DIR, exist_ok=True)


def gen_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_path(doc_id: str) -> str:
    return os.path.join(DATA_DIR, f"{doc_id}.json")


def _read_doc(doc_id: str) -> dict | None:
    path = _file_path(doc_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_doc(data: dict):
    path = _file_path(data["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_document(doc_id: str) -> dict | None:
    with _lock:
        return _read_doc(doc_id)


def list_documents() -> list[dict]:
    with _lock:
        docs = []
        if not os.path.exists(DATA_DIR):
            return docs
        for filename in sorted(os.listdir(DATA_DIR)):
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


def get_token(doc_id: str, token_id: str) -> dict | None:
    doc = get_document(doc_id)
    if not doc:
        return None
    for t in doc.get("tokens", []):
        if t["id"] == token_id:
            return t
    return None


def update_token(doc_id: str, token_id: str, updates: dict) -> dict | None:
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
        for key, value in updates.items():
            target[key] = value
        doc["updated_at"] = utcnow()
        _write_doc(doc)
        return target


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
            "ref_type": None,
            "ref_target_token_id": None,
            "ref_url": None,
            "ref_explanation": None,
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

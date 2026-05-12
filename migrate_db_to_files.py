"""One-time script to migrate data from SQLite / old JSON to new merged-token format."""
import json
import os
import uuid
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "intensivereading.db")
DATA_DIR = os.path.join(BASE_DIR, "data", "documents")


def _to_iso(raw: str) -> str:
    dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S.%f")
    return dt.replace(tzinfo=timezone.utc).isoformat()


def merge_tokens(raw_tokens: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    order: list[str] = []

    for t in raw_tokens:
        key = t["text"]
        if key not in groups:
            groups[key] = {
                "id": str(uuid.uuid4()),
                "start_offsets": [],
                "text": key,
                "style_type": t.get("style_type", "default") or "default",
                "ref_type": None,
                "ref_target_token_id": None,
                "ref_url": None,
                "ref_explanation": None,
            }
            order.append(key)
        existing = groups[key]
        existing["start_offsets"].append(t["start_offset"])
        if not any(existing.get(f) for f in ["ref_type", "ref_target_token_id", "ref_url", "ref_explanation"]):
            for f in ["ref_type", "ref_target_token_id", "ref_url", "ref_explanation"]:
                existing[f] = t.get(f) or None

    return [groups[k] for k in order]


os.makedirs(DATA_DIR, exist_ok=True)

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    docs = conn.execute("SELECT * FROM documents ORDER BY created_at").fetchall()

    for doc in docs:
        doc_id = doc["id"]
        tokens = conn.execute(
            "SELECT * FROM tokens WHERE document_id = ? ORDER BY start_offset", (doc_id,)
        ).fetchall()

        raw = []
        for t in tokens:
            raw.append({
                "start_offset": t["start_offset"],
                "text": t["text"],
                "style_type": t["style_type"] or "default",
                "ref_type": t["ref_type"] or None,
                "ref_target_token_id": t["ref_target_token_id"] or None,
                "ref_url": t["ref_url"] or None,
                "ref_explanation": t["ref_explanation"] or None,
            })

        merged = merge_tokens(raw)

        doc_data = {
            "id": doc_id,
            "title": doc["title"],
            "original_text": doc["original_text"],
            "created_at": _to_iso(doc["created_at"]) if doc["created_at"] else "",
            "updated_at": _to_iso(doc["updated_at"]) if doc["updated_at"] else "",
            "tokens": merged,
        }

        filepath = os.path.join(DATA_DIR, f"{doc_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(doc_data, f, ensure_ascii=False, indent=2)

        print(f"Migrated SQLite: {doc['title']} ({len(tokens)} pos -> {len(merged)} merged tokens) -> {filepath}")

    conn.close()
    print("SQLite migration done.")
else:
    print("No SQLite DB found, skipping.")

# Also migrate existing JSON files that use old format (start_offset vs start_offsets)
if os.path.exists(DATA_DIR):
    for filename in sorted(os.listdir(DATA_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            doc = json.load(f)

        tokens = doc.get("tokens", [])
        if not tokens:
            continue

        first = tokens[0]
        if "start_offsets" in first:
            continue  # already migrated

        raw = []
        for t in tokens:
            raw.append({
                "start_offset": t["start_offset"],
                "text": t["text"],
                "style_type": t.get("style_type", "default") or "default",
                "ref_type": t.get("ref_type"),
                "ref_target_token_id": t.get("ref_target_token_id"),
                "ref_url": t.get("ref_url"),
                "ref_explanation": t.get("ref_explanation"),
            })

        doc["tokens"] = merge_tokens(raw)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        print(f"Migrated JSON: {doc['title']} ({len(raw)} pos -> {len(doc['tokens'])} merged tokens)")

print("All done.")

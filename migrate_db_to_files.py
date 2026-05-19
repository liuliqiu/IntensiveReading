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
            }
            order.append(key)
        existing = groups[key]
        existing["start_offsets"].append(t["start_offset"])

    return [groups[k] for k in order]


def _migrate_refs(raw_tokens: list[dict], merged: list[dict]) -> list[dict]:
    """Build relations from old ref_* fields on raw tokens."""
    relations: list[dict] = []
    # Map old token start_offset+text -> new merged token id
    offset_map: dict[tuple[int, str], str] = {}
    for t in merged:
        for off in t["start_offsets"]:
            offset_map[(off, t["text"])] = t["id"]

    # Also need reverse: old token id -> new token id
    old_id_to_new: dict[str, str] = {}
    for t in raw_tokens:
        off = t["start_offset"]
        text = t["text"]
        if (off, text) in offset_map:
            old_id_to_new[t.get("_orig_id", "")] = offset_map[(off, text)]

    # Collect ref targets from old-style ref_target_token_id
    ref_targets = []
    for t in raw_tokens:
        rt = t.get("ref_type")
        if rt == "internal" and t.get("ref_target_token_id"):
            ref_targets.append({
                "old_source_id": t.get("_orig_id"),
                "old_target_id": t["ref_target_token_id"],
            })

    for t in raw_tokens:
        ref_type = t.get("ref_type")
        if not ref_type:
            continue
        rel: dict = {
            "id": str(uuid.uuid4()),
            "direction": "->",
        }
        off = t["start_offset"]
        text = t["text"]
        source_id = offset_map.get((off, text))
        if not source_id:
            continue
        rel["source_token_id"] = source_id

        if ref_type == "internal" and t.get("ref_target_token_id"):
            rel["type"] = "refers_to"
            # Find target in offset_map by old target id
            target_id = _resolve_target_id(t["ref_target_token_id"], raw_tokens, offset_map)
            if target_id:
                rel["target_token_id"] = target_id
            else:
                continue
        elif ref_type == "external" and t.get("ref_url"):
            rel["type"] = "links_to"
            rel["target_url"] = t["ref_url"]
        elif ref_type == "note" and t.get("ref_explanation"):
            rel["type"] = "annotates"
            rel["target_explanation"] = t["ref_explanation"]
        else:
            continue

        relations.append(rel)

    return relations


def _resolve_target_id(old_target_id: str, raw_tokens: list[dict], offset_map: dict) -> str | None:
    for t in raw_tokens:
        if t.get("_orig_id") == old_target_id:
            off = t["start_offset"]
            text = t["text"]
            return offset_map.get((off, text))
    return None


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
                "_orig_id": t["id"],
                "start_offset": t["start_offset"],
                "text": t["text"],
                "style_type": t["style_type"] or "default",
                "ref_type": t["ref_type"] or None,
                "ref_target_token_id": t["ref_target_token_id"] or None,
                "ref_url": t["ref_url"] or None,
                "ref_explanation": t["ref_explanation"] or None,
            })

        merged = merge_tokens(raw)
        relations = _migrate_refs(raw, merged)

        doc_data = {
            "id": doc_id,
            "title": doc["title"],
            "original_text": doc["original_text"],
            "created_at": _to_iso(doc["created_at"]) if doc["created_at"] else "",
            "updated_at": _to_iso(doc["updated_at"]) if doc["updated_at"] else "",
            "tokens": merged,
            "relations": relations,
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
                "_orig_id": t.get("id", ""),
                "start_offset": t["start_offset"],
                "text": t["text"],
                "style_type": t.get("style_type", "default") or "default",
                "ref_type": t.get("ref_type"),
                "ref_target_token_id": t.get("ref_target_token_id"),
                "ref_url": t.get("ref_url"),
                "ref_explanation": t.get("ref_explanation"),
            })

        merged = merge_tokens(raw)
        relations = _migrate_refs(raw, merged)

        doc["tokens"] = merged
        doc["relations"] = relations
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        print(f"Migrated JSON: {doc['title']} ({len(raw)} pos -> {len(doc['tokens'])} merged tokens)")

print("All done.")

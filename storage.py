import json
import os
import uuid
import threading
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "documents")
LAYERS_DIR = os.path.join(os.path.dirname(__file__), "data", "layers")

_lock = threading.RLock()


def init():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LAYERS_DIR, exist_ok=True)


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


def _migrate_refs_to_relations(doc: dict) -> dict:
    """Convert old inline ref_* fields on tokens into standalone relations."""
    relations = doc.get("relations", [])
    if isinstance(relations, list) and len(relations) > 0:
        return doc  # already migrated

    new_relations: list[dict] = []
    for t in doc.get("tokens", []):
        ref_type = t.get("ref_type")
        if not ref_type:
            continue
        rel: dict = {
            "id": gen_id(),
            "direction": "->",
            "source_token_id": t["id"],
        }
        if ref_type == "internal" and t.get("ref_target_token_id"):
            rel["type"] = "refers_to"
            rel["target_token_id"] = t["ref_target_token_id"]
        elif ref_type == "external" and t.get("ref_url"):
            rel["type"] = "links_to"
            rel["target_url"] = t["ref_url"]
        elif ref_type == "note" and t.get("ref_explanation"):
            rel["type"] = "annotates"
            rel["target_explanation"] = t["ref_explanation"]
        else:
            continue
        new_relations.append(rel)

    # Strip ref_* from tokens
    for t in doc["tokens"]:
        for f in ["ref_type", "ref_target_token_id", "ref_url", "ref_explanation"]:
            t.pop(f, None)

    doc["relations"] = new_relations
    return doc


def _migrate_relations_to_objects(doc: dict) -> dict:
    """Convert old Relation format (source_token_id/target_*) to new objects[] format."""
    relations = doc.get("relations", [])
    if not isinstance(relations, list):
        return doc

    new_relations: list[dict] = []
    for rel in relations:
        # Already in objects or members format
        if "objects" in rel or "members" in rel:
            new_relations.append(rel)
            continue

        objects: list[dict] = []

        # objects[0] = source
        if rel.get("source_token_id"):
            objects.append({
                "id": gen_id(),
                "token_id": rel["source_token_id"],
            })

        # objects[1] = target
        target_token_id = rel.get("target_token_id")
        target_url = rel.get("target_url")
        target_explanation = rel.get("target_explanation")

        if target_token_id:
            objects.append({
                "id": gen_id(),
                "token_id": target_token_id,
            })
        elif target_explanation:
            objects.append({
                "id": gen_id(),
                "text": target_explanation,
            })
        elif target_url:
            objects.append({
                "id": gen_id(),
                "text": target_url,
            })

        if len(objects) < 2:
            continue

        new_relations.append({
            "id": rel["id"],
            "type": rel.get("type", ""),
            "objects": objects,
        })

    doc["relations"] = new_relations
    return doc


def _migrate_objects_to_top_level(doc: dict) -> dict:
    """Extract embedded objects from Relations to top-level relation_objects pool,
    then convert Relations to use members referencing the pool."""
    has_objects = "relation_objects" in doc
    all_members = all("members" in r for r in doc.get("relations", []))

    if has_objects and all_members:
        return doc  # already fully migrated

    obj_pool: dict[str, dict] = {}
    if has_objects:
        for ro in doc.get("relation_objects", []):
            obj_pool[ro["id"]] = ro

    obj_by_token: dict[str, str] = {}
    new_relations: list[dict] = []

    for rel in doc.get("relations", []):
        # Already in members format
        if "members" in rel:
            new_relations.append(rel)
            continue

        members: list[dict] = []

        # Convert from embedded objects format
        objects = rel.get("objects", [])
        if objects:
            for o in objects:
                token_id = o.get("token_id")
                text = o.get("text")
                if token_id and token_id in obj_by_token:
                    members.append({"kind": "object", "id": obj_by_token[token_id]})
                else:
                    obj_id = o.get("id") or gen_id()
                    if obj_id not in obj_pool:
                        obj_pool[obj_id] = {
                            "id": obj_id,
                            "token_id": token_id,
                            "text": text,
                        }
                    if token_id:
                        obj_by_token[token_id] = obj_id
                    members.append({"kind": "object", "id": obj_id})

        # Convert from object_ids format
        obj_ids = rel.get("object_ids", [])
        if obj_ids:
            for oid in obj_ids:
                members.append({"kind": "object", "id": oid})

        if len(members) >= 2:
            new_relations.append({
                "id": rel["id"],
                "type": rel.get("type", ""),
                "members": members,
            })

    if not has_objects:
        doc["relation_objects"] = list(obj_pool.values())
    doc["relations"] = new_relations
    return doc


def _migrate_objects_add_kind(doc: dict) -> dict:
    for ro in doc.get("relation_objects", []):
        if "kind" not in ro:
            ro["kind"] = "manual"
    return doc


def get_document(doc_id: str) -> dict | None:
    with _lock:
        doc = _read_doc(doc_id)
        if doc:
            doc = _migrate_refs_to_relations(doc)
            doc = _migrate_relations_to_objects(doc)
            doc = _migrate_objects_to_top_level(doc)
            doc = _migrate_objects_add_kind(doc)
        return doc


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
                    data = _migrate_refs_to_relations(data)
                    data = _migrate_relations_to_objects(data)
                    data = _migrate_objects_to_top_level(data)
                    data = _migrate_objects_add_kind(data)
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
            doc = _migrate_refs_to_relations(doc) if doc else None
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

        # Remove relations and objects containing the old token (cascade through references)
        stale_obj_ids: set[str] = set()
        for ro in doc.get("relation_objects", []):
            if ro.get("token_id") == token_id:
                stale_obj_ids.add(ro["id"])
        doc["relation_objects"] = [
            ro for ro in doc.get("relation_objects", [])
            if ro["id"] not in stale_obj_ids
        ]

        # Cascade: find all relations referencing stale objects or stale relations
        stale_rel_ids: set[str] = set()
        relations = doc.get("relations", [])
        while True:
            new_stale: set[str] = set()
            for r in relations:
                if r["id"] in stale_rel_ids:
                    continue
                for m in r.get("members", []):
                    if m.get("kind") == "object" and m.get("id") in stale_obj_ids:
                        new_stale.add(r["id"])
                        break
                    if m.get("kind") == "relation" and m.get("id") in stale_rel_ids:
                        new_stale.add(r["id"])
                        break
            if not new_stale:
                break
            stale_rel_ids.update(new_stale)

        doc["relations"] = [r for r in relations if r["id"] not in stale_rel_ids]

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


# ── TextLayer CRUD ──

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


def get_layer(layer_id: str) -> dict | None:
    with _lock:
        return _read_layer(layer_id)


def list_layers(document_id: str) -> list[dict]:
    with _lock:
        layers: list[dict] = []
        if not os.path.exists(LAYERS_DIR):
            return layers
        for filename in sorted(os.listdir(LAYERS_DIR)):
            if filename.endswith(".json"):
                lid = filename[:-5]
                data = _read_layer(lid)
                if data and data.get("document_id") == document_id:
                    layers.append(data)
        layers.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
        return layers


def save_layer(data: dict):
    with _lock:
        _write_layer(data)


def delete_layer(layer_id: str):
    with _lock:
        lp = _layer_path(layer_id)
        if os.path.exists(lp):
            os.remove(lp)

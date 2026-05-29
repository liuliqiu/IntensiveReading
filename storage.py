import json
import os
import uuid
import threading
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "documents")
LAYERS_DIR = os.path.join(os.path.dirname(__file__), "data", "layers")
FILES_DIR = os.path.join(os.path.dirname(__file__), "data", "files")
KNOWLEDGE_PATH = os.path.join(os.path.dirname(__file__), "data", "knowledge.json")

_lock = threading.RLock()


def init():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LAYERS_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)
    _migrate_docs_to_knowledge()
    _migrate_remove_token_and_doc_id()


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


def get_knowledge() -> dict:
    with _lock:
        if not os.path.exists(KNOWLEDGE_PATH):
            return {"relation_objects": [], "relations": []}
        with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)


def save_knowledge(data: dict):
    with _lock:
        with open(KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def _migrate_docs_to_knowledge():
    knowledge = get_knowledge()
    if knowledge.get("relation_objects") or knowledge.get("relations"):
        return

    if not os.path.exists(DATA_DIR):
        save_knowledge({"relation_objects": [], "relations": []})
        return

    all_objects: list[dict] = []
    all_relations: list[dict] = []

    for filename in sorted(os.listdir(DATA_DIR)):
        if not filename.endswith(".json"):
            continue
        doc_id = filename[:-5]
        doc = _read_doc(doc_id)
        if not doc:
            continue

        for ro in doc.get("relation_objects", []):
            ro["document_id"] = doc["id"]
            all_objects.append(ro)

        for r in doc.get("relations", []):
            all_relations.append(r)

        doc["relation_objects"] = []
        doc["relations"] = []
        _write_doc(doc)

    save_knowledge({"relation_objects": all_objects, "relations": all_relations})


def _migrate_remove_token_and_doc_id():
    knowledge = get_knowledge()
    objects = knowledge.get("relation_objects", [])
    relations = knowledge.get("relations", [])

    needs_migration = any(
        "token_id" in ro or "document_id" in ro
        for ro in objects
    )
    if not needs_migration:
        return

    all_docs = {}
    if os.path.exists(DATA_DIR):
        for filename in sorted(os.listdir(DATA_DIR)):
            if filename.endswith(".json"):
                doc_id = filename[:-5]
                doc = _read_doc(doc_id)
                if doc:
                    all_docs[doc_id] = doc

    doc_obj_map: dict[str, str] = {}
    for doc_id, doc in all_docs.items():
        obj_id = gen_id()
        doc_obj_map[doc_id] = obj_id
        objects.append({
            "id": obj_id,
            "text": doc.get("title", ""),
            "kind": "document",
            "metadata": {"document_id": doc_id},
        })

    token_map: dict[str, str] = {}
    for doc_id, doc in all_docs.items():
        for t in doc.get("tokens", []):
            token_map[t["id"]] = t["text"]

    obj_doc_mapping: dict[str, str] = {}
    for ro in objects:
        ro_id = ro.get("id", "")

        if ro.get("token_id") and not ro.get("text"):
            token_text = token_map.get(ro["token_id"])
            if token_text:
                ro["text"] = token_text
        ro.pop("token_id", None)

        old_doc_id = ro.pop("document_id", None)
        if old_doc_id and ro.get("kind") != "document":
            obj_doc_mapping[ro_id] = old_doc_id

    merged_map: dict[str, str] = {}
    text_kind_to_id: dict[tuple[str, str], str] = {}
    deduped_objects: list[dict] = []

    for ro in objects:
        key = (ro.get("text") or "", ro.get("kind") or "")
        if key in text_kind_to_id:
            old_id = ro["id"]
            new_id = text_kind_to_id[key]
            merged_map[old_id] = new_id
            if old_id in obj_doc_mapping:
                obj_doc_mapping.setdefault(new_id, obj_doc_mapping[old_id])
        else:
            text_kind_to_id[key] = ro["id"]
            deduped_objects.append(ro)

    for rel in relations:
        for m in rel.get("members", []):
            if m.get("id") in merged_map:
                m["id"] = merged_map[m["id"]]

    for ro_id, doc_id in obj_doc_mapping.items():
        if ro_id in merged_map:
            continue
        doc_obj_id = doc_obj_map.get(doc_id)
        if not doc_obj_id:
            continue
        exists = any(
            r.get("type") == "belongs_to"
            and any(m.get("id") == ro_id for m in r.get("members", []))
            and any(m.get("id") == doc_obj_id for m in r.get("members", []))
            for r in relations
        )
        if not exists:
            relations.append({
                "id": gen_id(),
                "type": "belongs_to",
                "members": [
                    {"kind": "object", "id": ro_id},
                    {"kind": "object", "id": doc_obj_id},
                ],
            })

    knowledge["relation_objects"] = deduped_objects
    knowledge["relations"] = relations
    save_knowledge(knowledge)


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


# ── Uploaded file storage ──

def save_uploaded_file(layer_id: str, filename: str, content: bytes) -> str:
    """Save uploaded file to disk, return the file path relative to the project.
    Future binary files (PDF, Word, etc.) use this path in layer metadata."""
    safe_name = os.path.basename(filename)
    dest_dir = os.path.join(FILES_DIR, layer_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, safe_name)
    with open(dest_path, "wb") as f:
        f.write(content)
    return dest_path


def get_file_path(file_path: str) -> str | None:
    """Return absolute path of a saved uploaded file, or None if not found."""
    if os.path.exists(file_path):
        return file_path
    return None

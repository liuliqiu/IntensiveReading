"""Data migration functions. Transform old data schemas to current format."""

import os

from backend.storage.base import gen_id, _read_doc, _write_doc
from backend.storage import base as storage_base
from backend.storage.knowledge import get_knowledge, save_knowledge


def migrate_refs_to_relations(doc: dict) -> dict:
    """Convert old inline ref_* fields on tokens into standalone relations."""
    relations = doc.get("relations", [])
    if isinstance(relations, list) and len(relations) > 0:
        return doc

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

    for t in doc["tokens"]:
        for f in ["ref_type", "ref_target_token_id", "ref_url", "ref_explanation"]:
            t.pop(f, None)

    doc["relations"] = new_relations
    return doc


def migrate_relations_to_objects(doc: dict) -> dict:
    """Convert old Relation format (source_token_id/target_*) to objects[] format."""
    relations = doc.get("relations", [])
    if not isinstance(relations, list):
        return doc

    new_relations: list[dict] = []
    for rel in relations:
        if "objects" in rel or "members" in rel:
            new_relations.append(rel)
            continue

        objects: list[dict] = []

        if rel.get("source_token_id"):
            objects.append({
                "id": gen_id(),
                "token_id": rel["source_token_id"],
            })

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


def migrate_objects_to_top_level(doc: dict) -> dict:
    """Extract embedded objects to top-level relation_objects pool,
    then convert Relations to use members referencing the pool."""
    has_objects = "relation_objects" in doc
    all_members = all("members" in r for r in doc.get("relations", []))

    if has_objects and all_members:
        return doc

    obj_pool: dict[str, dict] = {}
    if has_objects:
        for ro in doc.get("relation_objects", []):
            obj_pool[ro["id"]] = ro

    obj_by_token: dict[str, str] = {}
    new_relations: list[dict] = []

    for rel in doc.get("relations", []):
        if "members" in rel:
            new_relations.append(rel)
            continue

        members: list[dict] = []

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


def migrate_objects_add_kind(doc: dict) -> dict:
    for ro in doc.get("relation_objects", []):
        if "kind" not in ro:
            ro["kind"] = "manual"
    return doc


def migrate_docs_to_knowledge():
    knowledge = get_knowledge()
    if knowledge.get("relation_objects") or knowledge.get("relations"):
        return

    if not os.path.exists(storage_base.DATA_DIR):
        save_knowledge({"relation_objects": [], "relations": []})
        return

    all_objects: list[dict] = []
    all_relations: list[dict] = []

    for filename in sorted(os.listdir(storage_base.DATA_DIR)):
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


def migrate_remove_token_and_doc_id():
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
    if os.path.exists(storage_base.DATA_DIR):
        for filename in sorted(os.listdir(storage_base.DATA_DIR)):
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

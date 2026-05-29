"""Shared helpers for routers."""

from fastapi import HTTPException
from backend.schemas.tokens import TokenSchema
from backend.schemas.documents import DocumentOut
from backend.schemas.layers import TextLayerOut
from backend.schemas.knowledge import RelationObjectSchema as ROS, RelationSchema
from backend.storage import gen_id, get_knowledge, save_knowledge


def ensure_doc_object(doc_id: str, doc_title: str) -> str:
    knowledge = get_knowledge()
    for ro in knowledge.get("relation_objects", []):
        if ro.get("kind") == "document" and ro.get("metadata", {}).get("document_id") == doc_id:
            return ro["id"]
    obj_id = gen_id()
    knowledge.setdefault("relation_objects", []).append({
        "id": obj_id,
        "text": doc_title,
        "kind": "document",
        "metadata": {"document_id": doc_id},
    })
    save_knowledge(knowledge)
    return obj_id


def create_belongs_to_rels(object_ids: list[str], doc_obj_id: str) -> list[dict]:
    return [{
        "id": gen_id(),
        "type": "belongs_to",
        "members": [
            {"kind": "object", "id": oid},
            {"kind": "object", "id": doc_obj_id},
        ],
    } for oid in object_ids]


def validate_tokens_cover_text(tokens: list[TokenSchema], original_text: str):
    positions = []
    for t in tokens:
        for off in t.start_offsets:
            positions.append((off, t.text, t.id))
    positions.sort(key=lambda x: x[0])

    cursor = 0
    for off, text, tid in positions:
        if off != cursor:
            raise HTTPException(
                status_code=400,
                detail=f"Token {tid}: expected start_offset {cursor}, got {off}",
            )
        actual = original_text[off:off + len(text)]
        if actual != text:
            raise HTTPException(
                status_code=400,
                detail=f"Token {tid}: expected '{text}' at offset {off}, got '{actual}'",
            )
        cursor = off + len(text)

    if cursor != len(original_text):
        raise HTTPException(
            status_code=400,
            detail=f"Total coverage {cursor} chars, original text is {len(original_text)} chars",
        )


def get_surrounding_context(text: str, term: str, window: int = 200) -> tuple[str, int, int]:
    pos = text.find(term)
    if pos == -1:
        return text[:window], 0, 0
    start = max(0, pos - window)
    end = min(len(text), pos + len(term) + window)
    return text[start:end], start, pos - start


def layer_to_out(layer: dict) -> TextLayerOut:
    return TextLayerOut(
        id=layer["id"],
        document_id=layer["document_id"],
        type=layer["type"],
        text=layer.get("text", ""),
        tokens=[TokenSchema(**t) for t in layer.get("tokens", [])],
        metadata=layer.get("metadata"),
        created_at=layer["created_at"],
        updated_at=layer["updated_at"],
    )


def doc_to_out(doc: dict) -> DocumentOut:
    knowledge = get_knowledge()
    return DocumentOut(
        id=doc["id"],
        title=doc["title"],
        original_text=doc["original_text"],
        source_url=doc.get("source_url", ""),
        source_type=doc.get("source_type", "text"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        tokens=[TokenSchema(**{k: v for k, v in t.items() if k != "ref_type"}) for t in doc["tokens"]],
        relation_objects=[ROS(**ro) for ro in knowledge.get("relation_objects", [])],
        relations=[RelationSchema(**r) for r in knowledge.get("relations", [])],
    )

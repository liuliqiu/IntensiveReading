"""Knowledge base routes."""

from fastapi import APIRouter, HTTPException
from backend.schemas.knowledge import (
    KnowledgeObjectCreate, KnowledgeRelationCreate, KnowledgeRelationUpdate, KnowledgeOut,
)
from backend.storage import (
    get_document, gen_id,
    get_knowledge, save_knowledge,
)
from backend.routers._helpers import ensure_doc_object

router = APIRouter(prefix="/api", tags=["knowledge"])


@router.get("/knowledge", response_model=KnowledgeOut)
def get_knowledge_route():
    k = get_knowledge()
    return KnowledgeOut(
        relation_objects=k.get("relation_objects", []),
        relations=k.get("relations", []),
    )


@router.post("/knowledge/objects", response_model=KnowledgeOut)
def create_knowledge_object(body: KnowledgeObjectCreate):
    knowledge = get_knowledge()

    obj = {
        "id": gen_id(),
        "text": body.text,
        "kind": body.kind,
    }

    for existing in knowledge.get("relation_objects", []):
        if existing.get("text") == body.text and existing.get("kind") == body.kind:
            obj = existing
            break
    else:
        knowledge.setdefault("relation_objects", []).append(obj)

    if body.document_id:
        doc = get_document(body.document_id)
        if doc:
            doc_obj_id = ensure_doc_object(body.document_id, doc["title"])
            exists = any(
                r.get("type") == "belongs_to"
                and any(m.get("id") == obj["id"] for m in r.get("members", []))
                and any(m.get("id") == doc_obj_id for m in r.get("members", []))
                for r in knowledge.get("relations", [])
            )
            if not exists:
                knowledge.setdefault("relations", []).append({
                    "id": gen_id(), "type": "belongs_to",
                    "members": [
                        {"kind": "object", "id": obj["id"]},
                        {"kind": "object", "id": doc_obj_id},
                    ],
                })

    save_knowledge(knowledge)
    return KnowledgeOut(
        relation_objects=knowledge["relation_objects"],
        relations=knowledge["relations"],
    )


@router.delete("/knowledge/objects/{object_id}", response_model=KnowledgeOut)
def delete_knowledge_object(object_id: str):
    knowledge = get_knowledge()

    for r in knowledge.get("relations", []):
        if r.get("type") != "belongs_to":
            for m in r.get("members", []):
                if m.get("id") == object_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot delete: object is referenced in non-belongs_to relations",
                    )

    knowledge["relations"] = [
        r for r in knowledge.get("relations", [])
        if r.get("type") != "belongs_to" or not any(
            m.get("id") == object_id for m in r.get("members", [])
        )
    ]

    knowledge["relation_objects"] = [
        ro for ro in knowledge.get("relation_objects", [])
        if ro["id"] != object_id
    ]

    save_knowledge(knowledge)
    return KnowledgeOut(
        relation_objects=knowledge["relation_objects"],
        relations=knowledge["relations"],
    )


@router.post("/knowledge/relations", response_model=KnowledgeOut)
def create_knowledge_relation(body: KnowledgeRelationCreate):
    knowledge = get_knowledge()
    knowledge.setdefault("relations", []).append({
        "id": gen_id(), "type": body.type,
        "members": [m.model_dump() for m in body.members],
        "description": body.description,
    })
    save_knowledge(knowledge)
    return KnowledgeOut(
        relation_objects=knowledge["relation_objects"],
        relations=knowledge["relations"],
    )


@router.put("/knowledge/relations/{relation_id}", response_model=KnowledgeOut)
def update_knowledge_relation(relation_id: str, body: KnowledgeRelationUpdate):
    knowledge = get_knowledge()

    for r in knowledge.get("relations", []):
        if r["id"] == relation_id:
            if body.type is not None:
                r["type"] = body.type
            if body.members is not None:
                r["members"] = [m.model_dump() for m in body.members]
            if body.description is not None:
                r["description"] = body.description
            break
    else:
        raise HTTPException(status_code=404, detail="Relation not found")

    save_knowledge(knowledge)
    return KnowledgeOut(
        relation_objects=knowledge["relation_objects"],
        relations=knowledge["relations"],
    )


@router.delete("/knowledge/relations/{relation_id}", response_model=KnowledgeOut)
def delete_knowledge_relation(relation_id: str):
    knowledge = get_knowledge()

    for r in knowledge.get("relations", []):
        for m in r.get("members", []):
            if m.get("kind") == "relation" and m.get("id") == relation_id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete: relation is referenced by another relation",
                )

    knowledge["relations"] = [
        r for r in knowledge.get("relations", [])
        if r["id"] != relation_id
    ]

    save_knowledge(knowledge)
    return KnowledgeOut(
        relation_objects=knowledge["relation_objects"],
        relations=knowledge["relations"],
    )

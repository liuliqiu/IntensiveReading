"""Layer routes: CRUD, summarize, concepts, explain."""

from fastapi import APIRouter, HTTPException
from backend.schemas.documents import DocumentOut
from backend.schemas.layers import (
    TextLayerCreate, TextLayerUpdate, TextLayerOut,
)
from backend.schemas.scrape import ExplainRequest
from backend.storage import (
    get_document, save_document, gen_id, utcnow,
    get_layer, list_layers, save_layer, delete_layer,
)
from backend.services.tokenizer import tokenize_with_vocabulary
from backend.routers._helpers import (
    validate_tokens_cover_text, doc_to_out, layer_to_out,
    get_surrounding_context,
)

router = APIRouter(prefix="/api", tags=["layers"])


@router.post("/documents/{doc_id}/layers", response_model=TextLayerOut)
def create_layer(doc_id: str, body: TextLayerCreate):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    layer_id = gen_id()
    now = utcnow()
    layer = {
        "id": layer_id, "document_id": doc_id,
        "type": body.type, "text": "", "tokens": [],
        "created_at": now, "updated_at": now,
    }
    if body.metadata:
        layer["metadata"] = body.metadata
    save_layer(layer)
    return layer_to_out(layer)


@router.get("/documents/{doc_id}/layers", response_model=list[TextLayerOut])
def list_layers_route(doc_id: str):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    layers = list_layers(doc_id)
    return [layer_to_out(l) for l in layers]


@router.get("/layers/{layer_id}", response_model=TextLayerOut)
def get_layer_route(layer_id: str):
    layer = get_layer(layer_id)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    return layer_to_out(layer)


@router.put("/layers/{layer_id}", response_model=TextLayerOut)
def update_layer(layer_id: str, body: TextLayerUpdate):
    layer = get_layer(layer_id)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    if layer["text"]:
        validate_tokens_cover_text(body.tokens, layer["text"])

    layer["tokens"] = [t.model_dump() for t in body.tokens]
    layer["updated_at"] = utcnow()
    save_layer(layer)
    return layer_to_out(get_layer(layer_id))


@router.delete("/layers/{layer_id}")
def delete_layer_route(layer_id: str):
    layer = get_layer(layer_id)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    delete_layer(layer_id)
    return {"ok": True}


@router.post("/layers/{layer_id}/summarize", response_model=TextLayerOut)
async def summarize_layer(layer_id: str):
    layer = get_layer(layer_id)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    if layer["type"] != "summary":
        raise HTTPException(status_code=400, detail="Layer type must be 'summary'")

    doc = get_document(layer["document_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Parent document not found")

    from backend.services.ai import summarize_text
    summary, _ = await summarize_text(doc["original_text"])

    layer_tokens, new_tokens = tokenize_with_vocabulary(summary, doc["tokens"])

    if new_tokens:
        doc_tokens_by_text: dict[str, dict] = {t["text"]: t for t in doc["tokens"]}
        for nt in new_tokens:
            if nt["text"] not in doc_tokens_by_text:
                doc["tokens"].append(nt)
        doc["updated_at"] = utcnow()
        save_document(doc)

    layer["text"] = summary
    layer["tokens"] = layer_tokens
    layer["updated_at"] = utcnow()
    save_layer(layer)

    return layer_to_out(layer)


@router.post("/layers/{layer_id}/concepts", response_model=DocumentOut)
async def analyze_layer_concepts(layer_id: str):
    layer = get_layer(layer_id)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    if layer["type"] != "summary":
        raise HTTPException(status_code=400, detail="Layer type must be 'summary'")
    if not layer.get("text"):
        raise HTTPException(status_code=400, detail="Layer has no summary text")

    doc = get_document(layer["document_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Parent document not found")

    from backend.services.ai import analyze_concepts
    from backend.storage import get_knowledge, save_knowledge
    from backend.routers._helpers import ensure_doc_object, create_belongs_to_rels

    concepts, relationships = await analyze_concepts(layer["text"])

    doc_obj_id = ensure_doc_object(doc["id"], doc["title"])

    knowledge = get_knowledge()
    concept_objects: dict[str, str] = {}
    concept_names: list[str] = []
    new_objects: list[dict] = []
    new_relations: list[dict] = []
    new_obj_ids: list[str] = []

    for c in concepts:
        obj_id = gen_id()
        concept_objects[c["text"]] = obj_id
        concept_names.append(c["text"])
        new_objects.append({"id": obj_id, "text": c["text"], "kind": "ai_concept"})
        new_obj_ids.append(obj_id)

        description = c.get("description", "")
        if description:
            desc_obj_id = gen_id()
            new_objects.append({"id": desc_obj_id, "text": description, "kind": "ai_concept_desc"})
            new_obj_ids.append(desc_obj_id)
            new_relations.append({
                "id": gen_id(), "type": "explains",
                "members": [
                    {"kind": "object", "id": obj_id},
                    {"kind": "object", "id": desc_obj_id},
                ],
            })

    new_relations.extend(create_belongs_to_rels(new_obj_ids, doc_obj_id))

    for r in relationships:
        src_id = concept_objects.get(r.get("source", ""))
        tgt_id = concept_objects.get(r.get("target", ""))
        if not src_id or not tgt_id:
            continue
        new_relations.append({
            "id": gen_id(), "type": r.get("type", ""),
            "description": r.get("description", ""),
            "members": [
                {"kind": "object", "id": src_id},
                {"kind": "object", "id": tgt_id},
            ],
        })

    knowledge.setdefault("relation_objects", []).extend(new_objects)
    knowledge.setdefault("relations", []).extend(new_relations)
    save_knowledge(knowledge)

    return doc_to_out(doc)


@router.post("/documents/{doc_id}/objects/{object_id}/explain", response_model=DocumentOut)
async def explain_object(doc_id: str, object_id: str, body: ExplainRequest = ExplainRequest()):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from backend.services.ai import explain_text
    from backend.storage import get_knowledge, save_knowledge
    from backend.routers._helpers import ensure_doc_object, create_belongs_to_rels

    knowledge_obj = get_knowledge()
    matched_ro = None
    target_text = None
    for ro in knowledge_obj.get("relation_objects", []):
        if ro["id"] == object_id:
            matched_ro = ro
            target_text = ro.get("text")
            break

    if not matched_ro or not target_text:
        raise HTTPException(status_code=404, detail="Relation object not found")

    context, start_pos, term_pos = get_surrounding_context(
        doc["original_text"], target_text, body.context_window)

    explanation = await explain_text(target_text, context)

    doc_obj_id = ensure_doc_object(doc_id, doc["title"])

    expl_obj_id = gen_id()
    knowledge_obj.setdefault("relation_objects", []).append({
        "id": expl_obj_id, "text": explanation, "kind": "ai_explanation",
    })

    belongs_to_rel = {
        "id": gen_id(), "type": "belongs_to",
        "members": [
            {"kind": "object", "id": expl_obj_id},
            {"kind": "object", "id": doc_obj_id},
        ],
    }
    knowledge_obj.setdefault("relations", []).append(belongs_to_rel)

    save_knowledge(knowledge_obj)

    return doc_to_out(doc)

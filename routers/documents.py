from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from storage import (
    get_document, list_documents, save_document, gen_id, utcnow,
    get_layer, list_layers, save_layer, delete_layer,
    get_knowledge, save_knowledge,
)
from services.tokenizer import tokenize_and_merge, tokenize_with_vocabulary, tokenize_with_concepts


def _bind_concept_token_ids(objects: list[dict], tokens: list[dict], document_id: str) -> None:
    bound = {ro["token_id"] for ro in objects if ro.get("token_id")}
    for ro in objects:
        if ro.get("token_id") or not ro.get("text"):
            continue
        for t in tokens:
            if t["text"] == ro["text"] and t["id"] not in bound:
                ro["token_id"] = t["id"]
                ro["document_id"] = document_id
                bound.add(t["id"])
                break


router = APIRouter(prefix="/api", tags=["documents"])


class DocumentCreate(BaseModel):
    title: str
    original_text: str


class TokenSchema(BaseModel):
    id: str
    start_offsets: list[int]
    text: str
    style_type: str = "default"

    class Config:
        from_attributes = True


class RelationObjectSchema(BaseModel):
    id: str
    token_id: str | None = None
    text: str | None = None
    kind: str | None = None

    class Config:
        from_attributes = True


class MemberSchema(BaseModel):
    kind: str
    id: str

    class Config:
        from_attributes = True


class RelationSchema(BaseModel):
    id: str
    type: str
    members: list[MemberSchema]
    description: str | None = None

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    tokens: list[TokenSchema]


class TokenSplitRequest(BaseModel):
    offsets_to_move: list[int]


class DocumentOut(BaseModel):
    id: str
    title: str
    original_text: str
    created_at: str
    updated_at: str
    tokens: list[TokenSchema]
    relation_objects: list[RelationObjectSchema] = []
    relations: list[RelationSchema] = []

    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    id: str
    title: str
    token_count: int
    created_at: str
    updated_at: str


class TextLayerCreate(BaseModel):
    type: str


class TextLayerUpdate(BaseModel):
    tokens: list[TokenSchema]


class TextLayerOut(BaseModel):
    id: str
    document_id: str
    type: str
    text: str
    tokens: list[TokenSchema]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ExplainRequest(BaseModel):
    context_window: int = 200


class ScrapeRequest(BaseModel):
    url: str


class ScrapeResponse(BaseModel):
    title: str
    content: str


class DocumentProcessResponse(BaseModel):
    document: DocumentOut
    summary_layer: TextLayerOut


def _validate_tokens_cover_text(tokens: list[TokenSchema], original_text: str):
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


@router.post("/documents", response_model=DocumentOut)
def create_document(doc: DocumentCreate):
    doc_id = gen_id()
    now = utcnow()
    merged_tokens = tokenize_and_merge(doc.original_text)

    document = {
        "id": doc_id,
        "title": doc.title,
        "original_text": doc.original_text,
        "created_at": now,
        "updated_at": now,
        "tokens": [
            {
                "id": t["id"],
                "start_offsets": t["start_offsets"],
                "text": t["text"],
                "style_type": t["style_type"],
            }
            for t in merged_tokens
        ],
    }

    save_document(document)
    return _doc_to_out(document)


@router.post("/documents/process", response_model=DocumentProcessResponse)
async def process_document(doc: DocumentCreate):
    doc_id = gen_id()
    now = utcnow()

    document = {
        "id": doc_id,
        "title": doc.title,
        "original_text": doc.original_text,
        "created_at": now,
        "updated_at": now,
        "tokens": [],
    }
    save_document(document)

    layer_id = gen_id()
    layer = {
        "id": layer_id,
        "document_id": doc_id,
        "type": "summary",
        "text": "",
        "tokens": [],
        "created_at": now,
        "updated_at": now,
    }
    save_layer(layer)

    from services.ai import summarize_text, analyze_concepts
    summary, _ = await summarize_text(doc.original_text)

    concepts, relationships = await analyze_concepts(summary)

    concept_objects: dict[str, str] = {}
    concept_names: list[str] = []
    new_objects: list[dict] = []
    new_relations: list[dict] = []
    for c in concepts:
        obj_id = gen_id()
        concept_objects[c["text"]] = obj_id
        concept_names.append(c["text"])
        new_objects.append({
            "id": obj_id,
            "token_id": None,
            "document_id": doc_id,
            "text": c["text"],
            "kind": "ai_concept",
        })

        description = c.get("description", "")
        if description:
            desc_obj_id = gen_id()
            new_objects.append({
                "id": desc_obj_id,
                "token_id": None,
                "document_id": doc_id,
                "text": description,
                "kind": "ai_concept_desc",
            })
            new_relations.append({
                "id": gen_id(),
                "type": "explains",
                "members": [
                    {"kind": "object", "id": obj_id},
                    {"kind": "object", "id": desc_obj_id},
                ],
            })

    for r in relationships:
        src_id = concept_objects.get(r.get("source", ""))
        tgt_id = concept_objects.get(r.get("target", ""))
        if not src_id or not tgt_id:
            continue
        new_relations.append({
            "id": gen_id(),
            "type": r.get("type", ""),
            "description": r.get("description", ""),
            "members": [
                {"kind": "object", "id": src_id},
                {"kind": "object", "id": tgt_id},
            ],
        })

    doc_tokens = tokenize_with_concepts(doc.original_text, concept_names)
    _bind_concept_token_ids(new_objects, doc_tokens, doc_id)

    knowledge = get_knowledge()
    knowledge.setdefault("relation_objects", []).extend(new_objects)
    knowledge.setdefault("relations", []).extend(new_relations)
    save_knowledge(knowledge)

    document["tokens"] = doc_tokens
    document["updated_at"] = utcnow()
    save_document(document)

    layer_tokens, new_tokens = tokenize_with_vocabulary(summary, doc_tokens)

    if new_tokens:
        doc_tokens_by_text: dict[str, dict] = {t["text"]: t for t in document["tokens"]}
        for nt in new_tokens:
            if nt["text"] not in doc_tokens_by_text:
                document["tokens"].append(nt)
        document["updated_at"] = utcnow()
        save_document(document)

    layer["text"] = summary
    layer["tokens"] = layer_tokens
    layer["updated_at"] = utcnow()
    save_layer(layer)

    updated_doc = get_document(doc_id)
    updated_layer = get_layer(layer_id)
    return DocumentProcessResponse(
        document=_doc_to_out(updated_doc),
        summary_layer=_layer_to_out(updated_layer),
    )


@router.get("/documents", response_model=list[DocumentListItem])
def list_documents_route():
    docs = list_documents()
    return [
        DocumentListItem(
            id=d["id"],
            title=d["title"],
            token_count=len(d.get("tokens", [])),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )
        for d in docs
    ]


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document_route(doc_id: str):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_out(doc)


@router.put("/documents/{doc_id}", response_model=DocumentOut)
def update_document(doc_id: str, body: DocumentUpdate):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    _validate_tokens_cover_text(body.tokens, doc["original_text"])

    doc["tokens"] = [t.model_dump() for t in body.tokens]
    doc["updated_at"] = utcnow()
    save_document(doc)

    return _doc_to_out(doc)


@router.post("/tokens/{token_id}/split", response_model=DocumentOut)
def split_token_route(token_id: str, body: TokenSplitRequest):
    from storage import split_token, find_token_doc_id
    doc_id = find_token_doc_id(token_id)
    if not doc_id:
        raise HTTPException(status_code=404, detail="Token not found")

    doc = split_token(doc_id, token_id, body.offsets_to_move)
    if not doc:
        raise HTTPException(
            status_code=400,
            detail="Cannot split: token must have at least two offsets, "
                   "and offsets_to_move must be a non-empty proper subset",
        )

    return _doc_to_out(doc)


# ── TextLayer routes ──

@router.post("/documents/{doc_id}/layers", response_model=TextLayerOut)
def create_layer(doc_id: str, body: TextLayerCreate):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    layer_id = gen_id()
    now = utcnow()
    layer = {
        "id": layer_id,
        "document_id": doc_id,
        "type": body.type,
        "text": "",
        "tokens": [],
        "created_at": now,
        "updated_at": now,
    }
    save_layer(layer)
    return _layer_to_out(layer)


@router.get("/documents/{doc_id}/layers", response_model=list[TextLayerOut])
def list_layers_route(doc_id: str):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    layers = list_layers(doc_id)
    return [_layer_to_out(l) for l in layers]


@router.get("/layers/{layer_id}", response_model=TextLayerOut)
def get_layer_route(layer_id: str):
    layer = get_layer(layer_id)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    return _layer_to_out(layer)


@router.put("/layers/{layer_id}", response_model=TextLayerOut)
def update_layer(layer_id: str, body: TextLayerUpdate):
    layer = get_layer(layer_id)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    if layer["text"]:
        _validate_tokens_cover_text(body.tokens, layer["text"])

    layer["tokens"] = [t.model_dump() for t in body.tokens]
    layer["updated_at"] = utcnow()
    save_layer(layer)

    updated = get_layer(layer_id)
    return _layer_to_out(updated)


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

    from services.ai import summarize_text
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

    return _layer_to_out(layer)


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

    from services.ai import analyze_concepts
    concepts, relationships = await analyze_concepts(layer["text"])

    doc_id = doc["id"]
    new_objects: list[dict] = []
    new_relations: list[dict] = []
    concept_objects: dict[str, str] = {}
    for c in concepts:
        obj_id = gen_id()
        concept_objects[c["text"]] = obj_id
        new_objects.append({
            "id": obj_id,
            "token_id": None,
            "document_id": doc_id,
            "text": c["text"],
            "kind": "ai_concept",
        })

        description = c.get("description", "")
        if description:
            desc_obj_id = gen_id()
            new_objects.append({
                "id": desc_obj_id,
                "token_id": None,
                "document_id": doc_id,
                "text": description,
                "kind": "ai_concept_desc",
            })
            new_relations.append({
                "id": gen_id(),
                "type": "explains",
                "members": [
                    {"kind": "object", "id": obj_id},
                    {"kind": "object", "id": desc_obj_id},
                ],
            })

    for r in relationships:
        src_id = concept_objects.get(r.get("source", ""))
        tgt_id = concept_objects.get(r.get("target", ""))
        if not src_id or not tgt_id:
            continue
        new_relations.append({
            "id": gen_id(),
            "type": r.get("type", ""),
            "description": r.get("description", ""),
            "members": [
                {"kind": "object", "id": src_id},
                {"kind": "object", "id": tgt_id},
            ],
        })

    _bind_concept_token_ids(new_objects, doc["tokens"], doc_id)

    knowledge = get_knowledge()
    knowledge.setdefault("relation_objects", []).extend(new_objects)
    knowledge.setdefault("relations", []).extend(new_relations)
    save_knowledge(knowledge)

    return _doc_to_out(doc)


@router.post("/documents/{doc_id}/objects/{object_id}/explain", response_model=DocumentOut)
async def explain_object(doc_id: str, object_id: str, body: ExplainRequest = ExplainRequest()):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    knowledge = get_knowledge()
    obj = None
    for ro in knowledge.get("relation_objects", []):
        if ro["id"] == object_id:
            obj = ro
            break
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")

    term_text = ""
    if obj.get("token_id"):
        for t in doc["tokens"]:
            if t["id"] == obj["token_id"]:
                term_text = t["text"]
                break
    if not term_text and obj.get("text"):
        term_text = obj["text"]

    context = _get_surrounding_context(doc["original_text"], term_text, body.context_window)

    from services.ai import explain_text
    explanation = await explain_text(term_text, context)

    new_obj_id = gen_id()
    new_obj = {
        "id": new_obj_id,
        "token_id": None,
        "document_id": doc_id,
        "text": explanation,
        "kind": "ai_explanation",
    }
    knowledge.setdefault("relation_objects", []).append(new_obj)

    new_rel = {
        "id": gen_id(),
        "type": "explains",
        "members": [
            {"kind": "object", "id": object_id},
            {"kind": "object", "id": new_obj_id},
        ],
    }
    knowledge.setdefault("relations", []).append(new_rel)
    save_knowledge(knowledge)

    return _doc_to_out(doc)


class KnowledgeObjectCreate(BaseModel):
    token_id: str | None = None
    document_id: str | None = None
    text: str | None = None
    kind: str = "manual"


class KnowledgeRelationCreate(BaseModel):
    type: str
    members: list[MemberSchema]
    description: str | None = None


class KnowledgeRelationUpdate(BaseModel):
    type: str | None = None
    members: list[MemberSchema] | None = None
    description: str | None = None


class KnowledgeOut(BaseModel):
    relation_objects: list[RelationObjectSchema]
    relations: list[RelationSchema]


@router.get("/knowledge", response_model=KnowledgeOut)
def get_knowledge_route():
    knowledge = get_knowledge()
    return KnowledgeOut(
        relation_objects=[RelationObjectSchema(**ro) for ro in knowledge.get("relation_objects", [])],
        relations=[RelationSchema(**r) for r in knowledge.get("relations", [])],
    )


@router.post("/knowledge/objects", response_model=KnowledgeOut)
def create_knowledge_object(body: KnowledgeObjectCreate):
    knowledge = get_knowledge()
    new_obj = body.model_dump()
    new_obj["id"] = gen_id()
    knowledge.setdefault("relation_objects", []).append(new_obj)
    save_knowledge(knowledge)
    return KnowledgeOut(
        relation_objects=[RelationObjectSchema(**ro) for ro in knowledge.get("relation_objects", [])],
        relations=[RelationSchema(**r) for r in knowledge.get("relations", [])],
    )


@router.delete("/knowledge/objects/{object_id}", response_model=KnowledgeOut)
def delete_knowledge_object(object_id: str):
    knowledge = get_knowledge()
    objects = knowledge.get("relation_objects", [])
    relations = knowledge.get("relations", [])

    ref_count = sum(
        1 for r in relations
        if any(m.get("id") == object_id for m in r.get("members", []))
    )
    if ref_count > 0:
        raise HTTPException(status_code=400, detail=f"Object is referenced by {ref_count} relations")

    knowledge["relation_objects"] = [ro for ro in objects if ro["id"] != object_id]
    save_knowledge(knowledge)
    return KnowledgeOut(
        relation_objects=[RelationObjectSchema(**ro) for ro in knowledge.get("relation_objects", [])],
        relations=[RelationSchema(**r) for r in knowledge.get("relations", [])],
    )


@router.post("/knowledge/relations", response_model=KnowledgeOut)
def create_knowledge_relation(body: KnowledgeRelationCreate):
    knowledge = get_knowledge()
    new_rel = body.model_dump()
    new_rel["id"] = gen_id()
    knowledge.setdefault("relations", []).append(new_rel)
    save_knowledge(knowledge)
    return KnowledgeOut(
        relation_objects=[RelationObjectSchema(**ro) for ro in knowledge.get("relation_objects", [])],
        relations=[RelationSchema(**r) for r in knowledge.get("relations", [])],
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
        relation_objects=[RelationObjectSchema(**ro) for ro in knowledge.get("relation_objects", [])],
        relations=[RelationSchema(**r) for r in knowledge.get("relations", [])],
    )


@router.delete("/knowledge/relations/{relation_id}", response_model=KnowledgeOut)
def delete_knowledge_relation(relation_id: str):
    knowledge = get_knowledge()
    relations = knowledge.get("relations", [])
    ref_count = sum(
        1 for r in relations
        if r["id"] != relation_id
        and any(m.get("kind") == "relation" and m.get("id") == relation_id for m in r.get("members", []))
    )
    if ref_count > 0:
        raise HTTPException(status_code=400, detail=f"Relation is referenced by {ref_count} relations")

    knowledge["relations"] = [r for r in relations if r["id"] != relation_id]
    save_knowledge(knowledge)
    return KnowledgeOut(
        relation_objects=[RelationObjectSchema(**ro) for ro in knowledge.get("relation_objects", [])],
        relations=[RelationSchema(**r) for r in knowledge.get("relations", [])],
    )


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url_route(body: ScrapeRequest):
    from services.scraper import scrape_url
    try:
        title, content = await scrape_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"抓取失败：{e}")
    return ScrapeResponse(title=title, content=content)


def _get_surrounding_context(text: str, term: str, window: int) -> str:
    idx = text.find(term)
    if idx == -1:
        return text[:window * 2]
    start = max(0, idx - window)
    end = min(len(text), idx + len(term) + window)
    return text[start:end]


def _layer_to_out(layer: dict) -> TextLayerOut:
    return TextLayerOut(
        id=layer["id"],
        document_id=layer["document_id"],
        type=layer["type"],
        text=layer.get("text", ""),
        tokens=[TokenSchema(**t) for t in layer.get("tokens", [])],
        created_at=layer["created_at"],
        updated_at=layer["updated_at"],
    )


def _doc_to_out(doc: dict) -> DocumentOut:
    knowledge = get_knowledge()
    return DocumentOut(
        id=doc["id"],
        title=doc["title"],
        original_text=doc["original_text"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        tokens=[TokenSchema(**{k: v for k, v in t.items() if k != "ref_type"}) for t in doc["tokens"]],
        relation_objects=[RelationObjectSchema(**ro) for ro in knowledge.get("relation_objects", [])],
        relations=[RelationSchema(**r) for r in knowledge.get("relations", [])],
    )

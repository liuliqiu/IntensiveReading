"""Document routes: CRUD, process, upload-file, token split."""

import os

from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.schemas.documents import (
    DocumentCreate, DocumentOut, DocumentListItem, DocumentUpdate,
    TokenSplitRequest, DocumentProcessResponse,
)
from backend.schemas.layers import TextLayerOut
from backend.storage import (
    get_document, list_documents, save_document, gen_id, utcnow,
    get_layer, list_layers, save_layer,
    get_knowledge, save_knowledge, split_token, find_token_doc_id,
)
from backend.services.tokenizer import tokenize_and_merge, tokenize_with_vocabulary, tokenize_with_concepts
from backend.services.file_parser import get_parser
from backend.routers._helpers import (
    ensure_doc_object, create_belongs_to_rels,
    validate_tokens_cover_text, doc_to_out, layer_to_out,
)

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/documents", response_model=DocumentOut)
def create_document(doc: DocumentCreate):
    doc_id = gen_id()
    now = utcnow()
    merged_tokens = tokenize_and_merge(doc.original_text)

    document = {
        "id": doc_id, "title": doc.title,
        "original_text": doc.original_text,
        "source_url": doc.source_url,
        "source_type": doc.source_type,
        "created_at": now, "updated_at": now,
        "tokens": [
            {
                "id": t["id"], "start_offsets": t["start_offsets"],
                "text": t["text"], "style_type": t["style_type"],
            }
            for t in merged_tokens
        ],
    }

    save_document(document)
    ensure_doc_object(doc_id, doc.title)
    return doc_to_out(document)


async def _run_ai_pipeline(original_text: str):
    from backend.services.ai import summarize_text, analyze_concepts
    summary, _ = await summarize_text(original_text)
    concepts, relationships = await analyze_concepts(summary)
    return summary, concepts, relationships


def _build_concept_objects(concepts, doc_obj_id):
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
    return concept_objects, concept_names, new_objects, new_relations


def _finalize_concept_tokens(document, concepts, relationships, concept_objects, concept_names,
                             new_objects, new_relations, summary_text, summary_layer):
    doc_tokens = tokenize_with_concepts(document["original_text"], concept_names)

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

    knowledge = get_knowledge()
    knowledge.setdefault("relation_objects", []).extend(new_objects)
    knowledge.setdefault("relations", []).extend(new_relations)
    save_knowledge(knowledge)

    document["tokens"] = doc_tokens
    document["updated_at"] = utcnow()
    save_document(document)

    layer_tokens, new_tokens = tokenize_with_vocabulary(summary_text, doc_tokens)
    if new_tokens:
        doc_tokens_by_text: dict[str, dict] = {t["text"]: t for t in document["tokens"]}
        for nt in new_tokens:
            if nt["text"] not in doc_tokens_by_text:
                document["tokens"].append(nt)
        document["updated_at"] = utcnow()
        save_document(document)

    summary_layer["text"] = summary_text
    summary_layer["tokens"] = layer_tokens
    summary_layer["updated_at"] = utcnow()
    save_layer(summary_layer)


@router.post("/documents/process", response_model=DocumentProcessResponse)
async def process_document(doc: DocumentCreate):
    doc_id = gen_id()
    now = utcnow()

    document = {
        "id": doc_id, "title": doc.title,
        "original_text": doc.original_text,
        "source_url": doc.source_url,
        "source_type": doc.source_type,
        "created_at": now, "updated_at": now,
        "tokens": [],
    }
    save_document(document)

    doc_obj_id = ensure_doc_object(doc_id, doc.title)

    layer_id = gen_id()
    summary_layer = {
        "id": layer_id, "document_id": doc_id, "type": "summary",
        "text": "", "tokens": [], "created_at": now, "updated_at": now,
    }
    save_layer(summary_layer)

    summary, concepts, relationships = await _run_ai_pipeline(doc.original_text)
    concept_objects, concept_names, new_objects, new_relations = \
        _build_concept_objects(concepts, doc_obj_id)
    _finalize_concept_tokens(document, concepts, relationships, concept_objects,
                             concept_names, new_objects, new_relations,
                             summary, summary_layer)

    updated_doc = get_document(doc_id)
    updated_layer = get_layer(layer_id)
    return DocumentProcessResponse(
        document=doc_to_out(updated_doc),
        summary_layer=layer_to_out(updated_layer),
        origin_file_layer=None,
    )


@router.post("/documents/upload-file", response_model=DocumentProcessResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = raw_bytes.decode("utf-8", errors="replace")

    ext = os.path.splitext(file.filename)[1].lower() or ".md"
    parse_fn = get_parser(ext)
    plain_text = parse_fn(raw_text)

    title = os.path.splitext(file.filename)[0]
    mimetype = file.content_type or ("text/markdown" if ext == ".md" else "application/octet-stream")

    doc_id = gen_id()
    now = utcnow()

    document = {
        "id": doc_id, "title": title, "original_text": plain_text,
        "source_url": "", "source_type": "file",
        "created_at": now, "updated_at": now, "tokens": [],
    }
    save_document(document)
    doc_obj_id = ensure_doc_object(doc_id, title)

    origin_layer_id = gen_id()
    origin_layer = {
        "id": origin_layer_id, "document_id": doc_id, "type": "origin_file",
        "text": raw_text, "tokens": [],
        "metadata": {
            "filename": os.path.basename(file.filename),
            "mimetype": mimetype,
            "extension": ext,
        },
        "created_at": now, "updated_at": now,
    }
    save_layer(origin_layer)

    summary_layer_id = gen_id()
    summary_layer = {
        "id": summary_layer_id, "document_id": doc_id, "type": "summary",
        "text": "", "tokens": [], "created_at": now, "updated_at": now,
    }
    save_layer(summary_layer)

    try:
        summary, concepts, relationships = await _run_ai_pipeline(plain_text)
    except Exception:
        summary = "（AI 摘要服务暂不可用）"
        concepts, relationships = [], []

    concept_objects, concept_names, new_objects, new_relations = \
        _build_concept_objects(concepts, doc_obj_id)
    _finalize_concept_tokens(document, concepts, relationships, concept_objects,
                             concept_names, new_objects, new_relations,
                             summary, summary_layer)

    updated_doc = get_document(doc_id)
    updated_summary = get_layer(summary_layer_id)
    updated_origin = get_layer(origin_layer_id)
    return DocumentProcessResponse(
        document=doc_to_out(updated_doc),
        summary_layer=layer_to_out(updated_summary),
        origin_file_layer=layer_to_out(updated_origin),
    )


@router.get("/documents", response_model=list[DocumentListItem])
def list_documents_route():
    docs = list_documents()
    return [
        DocumentListItem(
            id=d["id"], title=d["title"],
            token_count=len(d.get("tokens", [])),
            created_at=d["created_at"], updated_at=d["updated_at"],
        )
        for d in docs
    ]


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document_route(doc_id: str):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc_to_out(doc)


@router.put("/documents/{doc_id}", response_model=DocumentOut)
def update_document(doc_id: str, body: DocumentUpdate):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    validate_tokens_cover_text(body.tokens, doc["original_text"])

    doc["tokens"] = [t.model_dump() for t in body.tokens]
    doc["updated_at"] = utcnow()
    save_document(doc)
    return doc_to_out(doc)


@router.post("/tokens/{token_id}/split", response_model=DocumentOut)
def split_token_route(token_id: str, body: TokenSplitRequest):
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
    return doc_to_out(doc)

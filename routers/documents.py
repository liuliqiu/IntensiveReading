from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from storage import (
    get_document, list_documents, save_document, gen_id, utcnow,
)
from services.tokenizer import tokenize_and_merge

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

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    tokens: list[TokenSchema]
    relation_objects: list[RelationObjectSchema] = []
    relations: list[RelationSchema] = []


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
        "relations": [],
        "relation_objects": [],
    }

    save_document(document)
    return _doc_to_out(document)


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
    doc["relation_objects"] = [ro.model_dump() for ro in body.relation_objects]
    doc["relations"] = [r.model_dump() for r in body.relations]
    doc["updated_at"] = utcnow()
    save_document(doc)

    updated = get_document(doc_id)
    return _doc_to_out(updated)


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


def _doc_to_out(doc: dict) -> DocumentOut:
    return DocumentOut(
        id=doc["id"],
        title=doc["title"],
        original_text=doc["original_text"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        tokens=[TokenSchema(**{k: v for k, v in t.items() if k != "ref_type"}) for t in doc["tokens"]],
        relation_objects=[RelationObjectSchema(**ro) for ro in doc.get("relation_objects", [])],
        relations=[RelationSchema(**r) for r in doc.get("relations", [])],
    )

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from storage import (
    get_document, list_documents, save_document,
    update_token, split_token, find_token_doc_id, gen_id, utcnow,
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
    ref_type: str | None = None
    ref_target_token_id: str | None = None
    ref_url: str | None = None
    ref_explanation: str | None = None

    class Config:
        from_attributes = True


class TokenUpdate(BaseModel):
    style_type: str | None = None
    ref_type: str | None = None
    ref_target_token_id: str | None = None
    ref_url: str | None = None
    ref_explanation: str | None = None


class TokensUpdate(BaseModel):
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
                "ref_type": None,
                "ref_target_token_id": None,
                "ref_url": None,
                "ref_explanation": None,
            }
            for t in merged_tokens
        ],
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


@router.put("/documents/{doc_id}/tokens", response_model=list[TokenSchema])
def update_tokens(doc_id: str, body: TokensUpdate):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    _validate_tokens_cover_text(body.tokens, doc["original_text"])

    doc["tokens"] = [t.model_dump() for t in body.tokens]
    doc["updated_at"] = utcnow()
    save_document(doc)

    updated = get_document(doc_id)
    return [TokenSchema(**t) for t in updated["tokens"]]


@router.patch("/tokens/{token_id}", response_model=TokenSchema)
def update_token_route(token_id: str, body: TokenUpdate):
    doc_id = find_token_doc_id(token_id)
    if not doc_id:
        raise HTTPException(status_code=404, detail="Token not found")

    update_data = body.model_dump(exclude_unset=True)
    updated = update_token(doc_id, token_id, update_data)
    return TokenSchema(**updated)


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

    return _doc_to_out(doc)


def _doc_to_out(doc: dict) -> DocumentOut:
    return DocumentOut(
        id=doc["id"],
        title=doc["title"],
        original_text=doc["original_text"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        tokens=[TokenSchema(**t) for t in doc["tokens"]],
    )

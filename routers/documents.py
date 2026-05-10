from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, engine, Base
from models import Document, Token, gen_id
from services.tokenizer import tokenize_text

router = APIRouter(prefix="/api", tags=["documents"])

Base.metadata.create_all(bind=engine)


class DocumentCreate(BaseModel):
    title: str
    original_text: str


class TokenSchema(BaseModel):
    id: str
    start_offset: int
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


@router.post("/documents", response_model=DocumentOut)
def create_document(doc: DocumentCreate, db: Session = Depends(get_db)):
    document = Document(
        id=gen_id(),
        title=doc.title,
        original_text=doc.original_text,
    )
    db.add(document)

    raw_tokens = tokenize_text(doc.original_text)
    for t in raw_tokens:
        token = Token(
            id=t["id"],
            document_id=document.id,
            start_offset=t["start_offset"],
            text=t["text"],
            style_type=t["style_type"],
        )
        db.add(token)

    db.commit()
    db.refresh(document)
    return _doc_to_out(document)


@router.get("/documents", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.updated_at.desc()).all()
    return [
        DocumentListItem(
            id=d.id,
            title=d.title,
            token_count=len(d.tokens),
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
        )
        for d in docs
    ]


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_out(doc)


@router.put("/documents/{doc_id}/tokens", response_model=list[TokenSchema])
def update_tokens(doc_id: str, body: TokensUpdate, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    new_tokens = body.tokens
    token_texts = "".join(t.text for t in new_tokens)
    if token_texts != doc.original_text:
        raise HTTPException(
            status_code=400,
            detail=f"Token text concatenation does not match original text. "
                   f"Expected {len(doc.original_text)} chars, got {len(token_texts)}.",
        )

    db.query(Token).filter(Token.document_id == doc_id).delete()
    for t in new_tokens:
        token = Token(
            id=t.id,
            document_id=doc_id,
            start_offset=t.start_offset,
            text=t.text,
            style_type=t.style_type,
            ref_type=t.ref_type,
            ref_target_token_id=t.ref_target_token_id,
            ref_url=t.ref_url,
            ref_explanation=t.ref_explanation,
        )
        db.add(token)

    db.commit()
    updated = db.query(Token).filter(Token.document_id == doc_id).order_by(Token.start_offset).all()
    return [TokenSchema.model_validate(t) for t in updated]


@router.patch("/tokens/{token_id}", response_model=TokenSchema)
def update_token(token_id: str, body: TokenUpdate, db: Session = Depends(get_db)):
    token = db.query(Token).filter(Token.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(token, key, value)

    db.commit()
    db.refresh(token)
    return TokenSchema.model_validate(token)


def _doc_to_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        title=doc.title,
        original_text=doc.original_text,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
        tokens=[TokenSchema.model_validate(t) for t in doc.tokens],
    )

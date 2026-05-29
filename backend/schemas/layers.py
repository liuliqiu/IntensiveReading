from pydantic import BaseModel

from backend.schemas.tokens import TokenSchema


class TextLayerCreate(BaseModel):
    type: str
    metadata: dict | None = None


class TextLayerUpdate(BaseModel):
    tokens: list[TokenSchema]


class TextLayerOut(BaseModel):
    id: str
    document_id: str
    type: str
    text: str
    tokens: list[TokenSchema]
    metadata: dict | None = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

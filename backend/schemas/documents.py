from pydantic import BaseModel

from backend.schemas.tokens import TokenSchema
from backend.schemas.knowledge import RelationObjectSchema, RelationSchema
from backend.schemas.layers import TextLayerOut


class DocumentCreate(BaseModel):
    title: str
    original_text: str
    source_url: str = ""
    source_type: str = "text"
    tags: list[str] = []


class DocumentUpdate(BaseModel):
    tokens: list[TokenSchema]


class DocumentTitleUpdate(BaseModel):
    title: str


class DocumentTagsUpdate(BaseModel):
    tags: list[str]


class TokenSplitRequest(BaseModel):
    offsets_to_move: list[int]


class DocumentOut(BaseModel):
    id: str
    title: str
    original_text: str
    source_url: str = ""
    source_type: str = "text"
    tags: list[str] = []
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
    tags: list[str] = []
    token_count: int
    created_at: str
    updated_at: str


class DocumentProcessResponse(BaseModel):
    document: DocumentOut
    summary_layer: TextLayerOut
    origin_file_layer: TextLayerOut | None = None

from pydantic import BaseModel


class RelationObjectSchema(BaseModel):
    id: str
    text: str | None = None
    kind: str | None = None
    metadata: dict | None = None

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


class KnowledgeObjectCreate(BaseModel):
    text: str | None = None
    kind: str = "manual"
    document_id: str | None = None


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

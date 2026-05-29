"""Backward-compatible shim: re-export router and schemas from backend."""

from backend.routers.documents import router
from backend.schemas.tokens import *
from backend.schemas.documents import *
from backend.schemas.layers import *
from backend.schemas.knowledge import *
from backend.schemas.scrape import *

# Keep these for backward compatibility in tests
from backend.schemas.tokens import TokenSchema
from backend.schemas.documents import (
    DocumentCreate, DocumentUpdate, DocumentOut, DocumentListItem,
    TokenSplitRequest, DocumentProcessResponse,
)
from backend.schemas.layers import (
    TextLayerCreate, TextLayerUpdate, TextLayerOut,
)
from backend.schemas.knowledge import (
    RelationObjectSchema, MemberSchema, RelationSchema,
    KnowledgeObjectCreate, KnowledgeRelationCreate,
    KnowledgeRelationUpdate, KnowledgeOut,
)
from backend.schemas.scrape import (
    ScrapeRequest, ScrapeResponse, ExplainRequest,
)

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    original_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    tokens = relationship("Token", back_populates="document", cascade="all, delete-orphan",
                          order_by="Token.start_offset")


class Token(Base):
    __tablename__ = "tokens"

    id = Column(String, primary_key=True, default=gen_id)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    start_offset = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    style_type = Column(String, default="default")
    ref_type = Column(String, nullable=True)
    ref_target_token_id = Column(String, nullable=True)
    ref_url = Column(Text, nullable=True)
    ref_explanation = Column(Text, nullable=True)

    document = relationship("Document", back_populates="tokens")

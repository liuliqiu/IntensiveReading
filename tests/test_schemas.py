"""Tests for Pydantic schemas in routers/documents.py."""

import pytest
from pydantic import ValidationError
from routers.documents import (
    DocumentCreate, DocumentUpdate, DocumentOut, DocumentListItem,
    TextLayerCreate, TextLayerUpdate, TextLayerOut,
    TokenSchema, RelationObjectSchema, MemberSchema, RelationSchema,
    ScrapeRequest, ScrapeResponse,
)


def test_document_create_valid():
    doc = DocumentCreate(title="Test", original_text="Hello world")
    assert doc.title == "Test"
    assert doc.original_text == "Hello world"
    assert doc.source_url == ""
    assert doc.source_type == "text"


def test_document_create_defaults():
    doc = DocumentCreate(title="T", original_text="X", source_url="http://a.com")
    assert doc.source_url == "http://a.com"
    assert doc.source_type == "text"


def test_document_create_missing_title_fails():
    with pytest.raises(ValidationError):
        DocumentCreate(original_text="Hello")


def test_document_create_missing_text_fails():
    with pytest.raises(ValidationError):
        DocumentCreate(title="Hello")


def test_token_schema_valid():
    t = TokenSchema(id="t1", start_offsets=[0, 10], text="hello", style_type="keyword")
    assert t.id == "t1"
    assert t.style_type == "keyword"


def test_token_schema_default_style():
    t = TokenSchema(id="t1", start_offsets=[0], text="hello")
    assert t.style_type == "default"


def test_document_update():
    du = DocumentUpdate(tokens=[TokenSchema(id="t1", start_offsets=[0], text="hi")])
    assert len(du.tokens) == 1


def test_relation_object_schema():
    ro = RelationObjectSchema(id="ro1", text="AI", kind="manual")
    assert ro.text == "AI"
    assert ro.kind == "manual"


def test_member_schema():
    m = MemberSchema(kind="object", id="ro1")
    assert m.kind == "object"


def test_relation_schema():
    r = RelationSchema(
        id="r1",
        type="refers_to",
        members=[MemberSchema(kind="object", id="ro1")],
        description="desc",
    )
    assert r.type == "refers_to"
    assert r.description == "desc"


def test_text_layer_create():
    lc = TextLayerCreate(type="summary")
    assert lc.type == "summary"
    assert lc.metadata is None


def test_text_layer_create_with_metadata():
    lc = TextLayerCreate(type="origin_file", metadata={"filename": "test.md"})
    assert lc.type == "origin_file"
    assert lc.metadata == {"filename": "test.md"}


def test_text_layer_update():
    lu = TextLayerUpdate(tokens=[TokenSchema(id="t1", start_offsets=[0], text="x")])
    assert len(lu.tokens) == 1


def test_text_layer_out():
    lo = TextLayerOut(
        id="l1", document_id="d1", type="summary", text="text",
        tokens=[], metadata=None,
        created_at="2025-01-01T00:00:00+00:00",
        updated_at="2025-01-01T00:00:00+00:00",
    )
    assert lo.id == "l1"
    assert lo.metadata is None


def test_scrape_request():
    sr = ScrapeRequest(url="http://example.com")
    assert sr.url == "http://example.com"


def test_scrape_response():
    sr = ScrapeResponse(title="Title", content="Content")
    assert sr.title == "Title"
    assert sr.content == "Content"


def test_document_list_item():
    di = DocumentListItem(id="d1", title="T", token_count=5,
                          created_at="2025-01-01T00:00:00+00:00",
                          updated_at="2025-01-01T00:00:00+00:00")
    assert di.token_count == 5

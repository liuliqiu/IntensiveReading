"""Tests for document CRUD in storage."""

import os
import tempfile
import storage
import backend.storage.base as storage_base


def _setup_temp_storage(monkeypatch, tmp_path):
    """Point storage dirs to temp dir for isolated testing."""
    d = tmp_path / "documents"
    l = tmp_path / "layers"
    f = tmp_path / "files"
    k = tmp_path / "knowledge.json"
    d.mkdir(parents=True)
    l.mkdir(parents=True)
    f.mkdir(parents=True)
    k.write_text('{"relation_objects":[],"relations":[]}', encoding="utf-8")
    monkeypatch.setattr(storage_base, "DATA_DIR", str(d))
    monkeypatch.setattr(storage_base, "LAYERS_DIR", str(l))
    monkeypatch.setattr(storage_base, "FILES_DIR", str(f))
    monkeypatch.setattr(storage_base, "KNOWLEDGE_PATH", str(k))
    return str(d), str(l), str(f), str(k)


def make_doc(id_="d1", title="Test", text="Hello world"):
    return {
        "id": id_,
        "title": title,
        "original_text": text,
        "source_url": "",
        "source_type": "text",
        "created_at": storage.utcnow(),
        "updated_at": storage.utcnow(),
        "tokens": [
            {"id": "t1", "start_offsets": [0], "text": "Hello", "style_type": "default"},
            {"id": "t2", "start_offsets": [5], "text": "world", "style_type": "default"},
        ],
    }


def test_save_and_get_document(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    doc = make_doc()
    storage.save_document(doc)
    result = storage.get_document("d1")
    assert result is not None
    assert result["id"] == "d1"
    assert result["title"] == "Test"


def test_get_document_not_found(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    result = storage.get_document("nonexistent")
    assert result is None


def test_list_documents_empty(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    result = storage.list_documents()
    assert result == []


def test_list_documents_sorted(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    d1 = make_doc("d1", title="First")
    d2 = make_doc("d2", title="Second")
    storage.save_document(d1)
    storage.save_document(d2)
    result = storage.list_documents()
    assert len(result) == 2
    for r in result:
        assert "tokens" in r


def test_list_documents_skips_non_json(monkeypatch, tmp_path):
    data_dir, _, _, _ = _setup_temp_storage(monkeypatch, tmp_path)
    (tmp_path / "documents" / "readme.txt").write_text("hello")
    storage.save_document(make_doc("d1"))
    result = storage.list_documents()
    assert len(result) == 1
    assert result[0]["id"] == "d1"


def test_split_token_basic(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    doc = {
        "id": "d1", "title": "T", "original_text": "aa aa",
        "source_url": "", "source_type": "text",
        "created_at": storage.utcnow(), "updated_at": storage.utcnow(),
        "tokens": [
            {"id": "t1", "start_offsets": [0, 3], "text": "aa", "style_type": "default"},
        ],
    }
    storage.save_document(doc)
    result = storage.split_token("d1", "t1", [3])
    assert result is not None
    assert len(result["tokens"]) == 2
    # Original token should have remaining offset
    t1 = next(t for t in result["tokens"] if t["id"] == "t1")
    assert t1["start_offsets"] == [0]
    # New token should have the moved offset
    t_new = next(t for t in result["tokens"] if t["id"] != "t1")
    assert t_new["start_offsets"] == [3]
    assert t_new["style_type"] == "default"


def test_split_token_single_offset_fails(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    doc = {
        "id": "d1", "title": "T", "original_text": "aa",
        "source_url": "", "source_type": "text",
        "created_at": storage.utcnow(), "updated_at": storage.utcnow(),
        "tokens": [
            {"id": "t1", "start_offsets": [0], "text": "aa", "style_type": "default"},
        ],
    }
    storage.save_document(doc)
    result = storage.split_token("d1", "t1", [0])
    assert result is None


def test_split_token_all_offsets_moved_fails(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    doc = {
        "id": "d1", "title": "T", "original_text": "aa bb aa",
        "source_url": "", "source_type": "text",
        "created_at": storage.utcnow(), "updated_at": storage.utcnow(),
        "tokens": [
            {"id": "t1", "start_offsets": [0, 3], "text": "aa", "style_type": "default"},
        ],
    }
    storage.save_document(doc)
    result = storage.split_token("d1", "t1", [0, 3])
    assert result is None


def test_find_token_doc_id(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    doc = make_doc()
    storage.save_document(doc)
    result = storage.find_token_doc_id("t1")
    assert result == "d1"


def test_find_token_doc_id_not_found(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    storage.save_document(make_doc())
    result = storage.find_token_doc_id("nonexistent")
    assert result is None

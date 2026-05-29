"""Tests for layer CRUD in storage."""

import storage
import backend.storage.base as storage_base


def _setup_temp_storage(monkeypatch, tmp_path):
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


def make_layer(id_="l1", doc_id="d1", type_="summary", text="Summary text"):
    return {
        "id": id_,
        "document_id": doc_id,
        "type": type_,
        "text": text,
        "tokens": [],
        "metadata": None,
        "created_at": storage.utcnow(),
        "updated_at": storage.utcnow(),
    }


def test_save_and_get_layer(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    layer = make_layer()
    storage.save_layer(layer)
    result = storage.get_layer("l1")
    assert result is not None
    assert result["id"] == "l1"
    assert result["document_id"] == "d1"


def test_get_layer_not_found(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    result = storage.get_layer("nonexistent")
    assert result is None


def test_list_layers_filters_by_document(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    storage.save_layer(make_layer("l1", "d1", type_="summary"))
    storage.save_layer(make_layer("l2", "d2", type_="summary"))
    storage.save_layer(make_layer("l3", "d1", type_="origin_file"))

    result = storage.list_layers("d1")
    assert len(result) == 2
    ids = {r["id"] for r in result}
    assert ids == {"l1", "l3"}


def test_list_layers_empty(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    result = storage.list_layers("d1")
    assert result == []


def test_list_layers_sorted_by_updated(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    l1 = make_layer("l1", "d1")
    l2 = make_layer("l2", "d1")
    l2["updated_at"] = "2025-01-01T00:00:00+00:00"
    l1["updated_at"] = "2025-01-02T00:00:00+00:00"
    storage.save_layer(l1)
    storage.save_layer(l2)
    result = storage.list_layers("d1")
    assert result[0]["id"] == "l1"


def test_delete_layer(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    layer = make_layer()
    storage.save_layer(layer)
    storage.delete_layer("l1")
    result = storage.get_layer("l1")
    assert result is None


def test_delete_nonexistent_layer_no_error(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    storage.delete_layer("nonexistent")


def test_layer_preserves_metadata(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    layer = make_layer("l1", "d1", type_="origin_file", text="# Markdown")
    layer["metadata"] = {"filename": "test.md", "mimetype": "text/markdown"}
    storage.save_layer(layer)
    result = storage.get_layer("l1")
    assert result["metadata"] == {"filename": "test.md", "mimetype": "text/markdown"}

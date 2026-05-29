"""Tests for knowledge CRUD in storage."""

import json
import storage
import backend.storage.base as storage_base


def _setup_temp_storage(monkeypatch, tmp_path):
    k = tmp_path / "knowledge.json"
    k.write_text('{"relation_objects":[],"relations":[]}', encoding="utf-8")
    monkeypatch.setattr(storage_base, "KNOWLEDGE_PATH", str(k))
    return str(k)


def test_get_knowledge_empty(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    result = storage.get_knowledge()
    assert result["relation_objects"] == []
    assert result["relations"] == []


def test_get_knowledge_file_not_exists_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_base, "KNOWLEDGE_PATH", "/nonexistent/path.json")
    result = storage.get_knowledge()
    assert result["relation_objects"] == []
    assert result["relations"] == []


def test_save_and_get_knowledge(monkeypatch, tmp_path):
    kp = _setup_temp_storage(monkeypatch, tmp_path)
    data = {
        "relation_objects": [
            {"id": "ro1", "text": "AI", "kind": "manual"},
        ],
        "relations": [
            {"id": "r1", "type": "refers_to", "members": [{"kind": "object", "id": "ro1"}]},
        ],
    }
    storage.save_knowledge(data)
    result = storage.get_knowledge()
    assert result is not None
    assert len(result["relation_objects"]) == 1
    assert result["relation_objects"][0]["text"] == "AI"
    assert len(result["relations"]) == 1


def test_save_knowledge_writes_to_disk(monkeypatch, tmp_path):
    kp = _setup_temp_storage(monkeypatch, tmp_path)
    storage.save_knowledge({"relation_objects": [], "relations": []})
    with open(kp, "r", encoding="utf-8") as f:
        raw = json.load(f)
    assert "relation_objects" in raw
    assert "relations" in raw

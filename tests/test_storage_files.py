"""Tests for uploaded file storage functions."""

import storage
import backend.storage.base as storage_base


def _setup_temp_storage(monkeypatch, tmp_path):
    f = tmp_path / "files"
    f.mkdir(parents=True)
    monkeypatch.setattr(storage_base, "FILES_DIR", str(f))
    return str(f)


def test_save_uploaded_file(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    path = storage.save_uploaded_file("layer1", "test.md", b"# Hello")
    assert path.endswith("test.md")
    import os
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read() == b"# Hello"


def test_save_uploaded_file_sanitizes_filename(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    path = storage.save_uploaded_file("layer1", "../etc/passwd", b"safe")
    import os
    assert ".." not in path
    assert os.path.basename(path) == "passwd"


def test_get_file_path_exists(monkeypatch, tmp_path):
    _setup_temp_storage(monkeypatch, tmp_path)
    path = storage.save_uploaded_file("layer1", "doc.md", b"content")
    result = storage.get_file_path(path)
    assert result == path


def test_get_file_path_not_exists():
    result = storage.get_file_path("/nonexistent/path/file.txt")
    assert result is None

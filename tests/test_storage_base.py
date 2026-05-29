"""Tests for storage base utilities: gen_id, utcnow."""

import storage
import backend.storage.base as storage_base


def test_gen_id_returns_string():
    result = storage.gen_id()
    assert isinstance(result, str)
    assert len(result) == 36


def test_gen_id_unique():
    ids = {storage.gen_id() for _ in range(100)}
    assert len(ids) == 100


def test_utcnow_returns_iso_format():
    result = storage.utcnow()
    assert isinstance(result, str)
    assert "T" in result
    assert "+" in result or result.endswith("Z")


def test_utcnow_is_timezone_aware_string():
    result = storage.utcnow()
    # Should contain timezone offset (+00:00) or Z
    from datetime import datetime
    dt = datetime.fromisoformat(result)
    assert dt.tzinfo is not None


def test_dirs_exist():
    storage.init()
    import os
    assert os.path.isdir(storage_base.DATA_DIR)
    assert os.path.isdir(storage_base.LAYERS_DIR)
    assert os.path.isdir(storage_base.FILES_DIR)

"""TextLayer CRUD."""

import os

from backend.storage.base import _lock, _read_layer, _write_layer, _layer_path
from backend.storage import base as storage_base


def get_layer(layer_id: str) -> dict | None:
    with _lock:
        return _read_layer(layer_id)


def list_layers(document_id: str) -> list[dict]:
    with _lock:
        layers: list[dict] = []
        if not os.path.exists(storage_base.LAYERS_DIR):
            return layers
        for filename in sorted(os.listdir(storage_base.LAYERS_DIR)):
            if filename.endswith(".json"):
                lid = filename[:-5]
                data = _read_layer(lid)
                if data and data.get("document_id") == document_id:
                    layers.append(data)
        layers.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
        return layers


def save_layer(data: dict):
    with _lock:
        _write_layer(data)


def delete_layer(layer_id: str):
    with _lock:
        lp = _layer_path(layer_id)
        if os.path.exists(lp):
            os.remove(lp)

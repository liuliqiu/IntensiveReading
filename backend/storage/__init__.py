"""Storage package: re-export all public functions + init."""

import os

from backend.storage.base import gen_id, utcnow
from backend.storage.documents import (
    get_document, list_documents, save_document,
    split_token, find_token_doc_id,
)
from backend.storage.layers import (
    get_layer, list_layers, save_layer, delete_layer,
)
from backend.storage.knowledge import get_knowledge, save_knowledge
from backend.storage.files import save_uploaded_file, get_file_path
from backend.storage.migrations import migrate_docs_to_knowledge, migrate_remove_token_and_doc_id
from backend.storage.base import DATA_DIR, LAYERS_DIR, FILES_DIR


def init():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LAYERS_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)
    migrate_docs_to_knowledge()
    migrate_remove_token_and_doc_id()

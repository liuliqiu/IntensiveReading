"""Centralized configuration for the backend."""

import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

DATA_DIR = os.path.join(_PROJECT_ROOT, "data", "documents")
LAYERS_DIR = os.path.join(_PROJECT_ROOT, "data", "layers")
FILES_DIR = os.path.join(_PROJECT_ROOT, "data", "files")
KNOWLEDGE_PATH = os.path.join(_PROJECT_ROOT, "data", "knowledge.json")

CORS_ORIGINS = ["http://localhost:5173"]

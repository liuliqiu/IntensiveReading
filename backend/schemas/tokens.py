"""Shared Token schema - used by both documents and layers."""

from pydantic import BaseModel


class TokenSchema(BaseModel):
    id: str
    start_offsets: list[int]
    text: str
    style_type: str = "default"

    class Config:
        from_attributes = True

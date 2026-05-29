from pydantic import BaseModel


class ExplainRequest(BaseModel):
    context_window: int = 200


class ScrapeRequest(BaseModel):
    url: str


class ScrapeResponse(BaseModel):
    title: str
    content: str

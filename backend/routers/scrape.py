"""Scrape route."""

from fastapi import APIRouter
from backend.schemas.scrape import ScrapeRequest, ScrapeResponse
from backend.services.scraper import scrape_url

router = APIRouter(prefix="/api", tags=["scrape"])


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url_route(body: ScrapeRequest):
    title, content = await scrape_url(body.url)
    return ScrapeResponse(title=title, content=content)

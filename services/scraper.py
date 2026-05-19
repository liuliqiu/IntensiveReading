import re
import httpx
import trafilatura
from trafilatura.metadata import extract_metadata
from bs4 import BeautifulSoup

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_MIN_CONTENT_LENGTH = 200


def _extract_title(html: str) -> str:
    metadata = extract_metadata(html)
    title = metadata.title.strip() if metadata and metadata.title else ""

    if not title:
        match = re.search(
            r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL
        )
        if match:
            title = BeautifulSoup(match.group(1), "html.parser").get_text().strip()

    return title


def _extract_text(html: str) -> str:
    text = trafilatura.extract(
        html,
        include_links=False,
        include_images=False,
        include_tables=False,
        deduplicate=True,
    )
    return (text or "").strip()


def _is_spa_shell(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if not body:
        return True

    for tag in body.find_all(["script", "style", "noscript"]):
        tag.decompose()

    content_tags = body.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "article", "main", "section"]
    )
    for tag in content_tags:
        if len(tag.get_text().strip()) > 20:
            return False

    body_text = body.get_text().strip()
    return len(body_text) < _MIN_CONTENT_LENGTH


async def _render_with_browser(url: str) -> tuple[str, str]:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            rendered_html = await page.content()
            title = await page.title()
            return rendered_html, title
        finally:
            await browser.close()


async def scrape_url(url: str) -> tuple[str, str]:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": _USER_AGENT})
        resp.raise_for_status()
        html = resp.text

    if not html.strip():
        raise ValueError("网页内容为空")

    title = _extract_title(html)
    text = _extract_text(html)

    if _is_spa_shell(html):
        rendered_html, js_title = await _render_with_browser(url)
        title = js_title or title
        text = _extract_text(rendered_html)

    if not text:
        raise ValueError("无法提取网页正文内容")

    return title or "", text

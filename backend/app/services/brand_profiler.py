"""Scrape a brand's homepage and extract a structured profile via Claude Haiku 4.5."""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.llm.client import extract_structured
from app.llm.prompts import BRAND_PROFILE_SYSTEM
from app.models import BrandProfile


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _fetch_and_clean(url: str, max_chars: int = 15000) -> str:
    """Fetch a URL and return cleaned visible text, capped at max_chars."""
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=HEADERS) as c:
        r = c.get(url)
        r.raise_for_status()
        html = r.text

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "meta", "link"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # collapse whitespace
    text = " ".join(text.split())
    return text[:max_chars]


def profile_brand(name: str, url: str) -> BrandProfile:
    """Scrape the brand homepage and extract a BrandProfile via Claude Haiku 4.5."""
    page_text = _fetch_and_clean(url)

    user_message = (
        f"Brand name: {name}\n"
        f"URL: {url}\n\n"
        f"Scraped page text:\n{page_text}"
    )

    return extract_structured(
        model=settings.model_haiku,
        system=BRAND_PROFILE_SYSTEM,
        user_content=user_message,
        response_schema=BrandProfile,
        max_tokens=1500,
    )


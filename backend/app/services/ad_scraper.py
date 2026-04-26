"""Scrape competitor ads via apify/facebook-ads-scraper.

Handles messy real-world Meta ad data:
- DCO/DPA ads with {{template.placeholders}} at top level → falls back to cards[0]
- Multi-language variants → drops non-English
- Variable format enums (IMAGE/CAROUSEL/DCO/DPA/VIDEO) → normalized to image/carousel
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import httpx
from apify_client import ApifyClient
from pydantic import BaseModel

from app.config import settings

ACTOR_ID = "apify/facebook-ads-scraper"

TEMPLATE_RE = re.compile(r"\{\{[^}]+\}\}")


class NormalizedAd(BaseModel):
    meta_ad_id: str
    format: str  # "image" or "carousel"
    creative_urls: list[str]
    local_image_paths: list[str]
    primary_text: str | None = None
    headline: str | None = None
    cta_text: str | None = None
    page_name: str | None = None
    start_date: str | None = None
    raw_payload: dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_template_placeholders(text: str | None) -> bool:
    """True if text contains Meta's {{dynamic.placeholders}}."""
    return bool(text) and bool(TEMPLATE_RE.search(text or ""))


def _is_english(text: str | None, min_ratio: float = 0.6) -> bool:
    """Heuristic: >=60% of alpha chars must be ASCII (drops Chinese/Arabic/etc)."""
    if not text:
        return True  # empty text doesn't disqualify the ad
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return True
    ascii_alpha = [c for c in alpha if ord(c) < 128]
    return (len(ascii_alpha) / len(alpha)) >= min_ratio


def _first_card(snapshot: dict) -> dict | None:
    cards = snapshot.get("cards") or []
    return cards[0] if cards else None


def _resolve_copy(snapshot: dict) -> tuple[str | None, str | None, str | None]:
    """Return (primary_text, headline, cta_text), unwrapping DCO/DPA templates.

    Strategy:
    1. Try top-level body.text / title / ctaText.
    2. If those are templates or empty, fall back to cards[0].body / title / ctaText.
    """
    body = snapshot.get("body") or {}
    primary = body.get("text") if isinstance(body, dict) else None
    headline = snapshot.get("title")
    cta = snapshot.get("ctaText")

    if _has_template_placeholders(primary) or not primary:
        card = _first_card(snapshot)
        if card:
            primary = card.get("body") or primary

    if _has_template_placeholders(headline) or not headline:
        card = _first_card(snapshot)
        if card:
            headline = card.get("title") or headline

    if not cta:
        card = _first_card(snapshot)
        if card:
            cta = card.get("ctaText") or cta

    return primary, headline, cta


def _classify_format(snapshot: dict) -> str | None:
    """Return 'image', 'carousel', or None (for video/unknown/drop)."""
    fmt = (snapshot.get("displayFormat") or "").upper()
    cards = snapshot.get("cards") or []
    images = snapshot.get("images") or []
    videos = snapshot.get("videos") or []

    if fmt == "VIDEO" or videos:
        return None
    if fmt == "CAROUSEL":
        return "carousel"
    if fmt == "IMAGE":
        return "image"
    # DCO / DPA / unknown — infer from structure
    if len(cards) > 1:
        return "carousel"
    if images or cards:
        return "image"
    return None


def _extract_creative_urls(snapshot: dict) -> list[str]:
    urls: list[str] = []
    for img in (snapshot.get("images") or []):
        url = img.get("originalImageUrl") or img.get("resizedImageUrl")
        if url:
            urls.append(url)
    for card in (snapshot.get("cards") or []):
        url = card.get("originalImageUrl") or card.get("resizedImageUrl")
        if url:
            urls.append(url)
    return urls


def _download_image(url: str, dest_dir: Path, index: int) -> str | None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{index}.jpg"
    if dest.exists():
        return str(dest)
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
            dest.write_bytes(r.content)
        return str(dest)
    except Exception as e:
        print(f"  ⚠  Failed to download image: {e}")
        return None


def _normalize_item(item: dict) -> NormalizedAd | None:
    snapshot = item.get("snapshot") or {}
    meta_ad_id = item.get("adArchiveID") or item.get("adArchiveId")
    if not meta_ad_id:
        return None

    our_format = _classify_format(snapshot)
    if our_format is None:
        return None  # video or unclassifiable

    primary_text, headline, cta_text = _resolve_copy(snapshot)

    # Drop non-English ads (based on the primary text that drives copy analysis)
    if primary_text and not _is_english(primary_text):
        return None

    # If primary_text is still a template placeholder, we can't analyze this ad
    if _has_template_placeholders(primary_text):
        return None

    creative_urls = _extract_creative_urls(snapshot)
    if not creative_urls:
        return None

    ad_cache_dir = settings.image_cache_path / str(meta_ad_id)
    local_paths: list[str] = []
    for idx, url in enumerate(creative_urls[:5]):
        local = _download_image(url, ad_cache_dir, idx)
        if local:
            local_paths.append(local)

    return NormalizedAd(
        meta_ad_id=str(meta_ad_id),
        format=our_format,
        creative_urls=creative_urls,
        local_image_paths=local_paths,
        primary_text=primary_text,
        headline=headline,
        cta_text=cta_text,
        page_name=snapshot.get("pageName") or item.get("pageName"),
        start_date=item.get("startDateFormatted"),
        raw_payload=item,
    )


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def scrape_competitor(
    facebook_url: str,
    max_ads: int = 6,
    results_limit: int = 25,
) -> list[NormalizedAd]:
    """Scrape, filter, sort by recency, normalize. Returns up to `max_ads` clean ads."""
    client = ApifyClient(settings.apify_api_token)

    run = client.actor(ACTOR_ID).call(run_input={
        "startUrls": [{"url": facebook_url}],
        "resultsLimit": results_limit,
        "isDetailsPerAd": False,
        "includeAboutPage": False,
        "onlyTotal": False,
    })
    if run is None:
        raise RuntimeError(f"Apify run failed for {facebook_url}")

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    # Sort newest first BEFORE normalization (cheaper than normalizing all)
    items.sort(key=lambda i: i.get("startDateFormatted") or "", reverse=True)

    normalized: list[NormalizedAd] = []
    for item in items:
        nad = _normalize_item(item)
        if nad:
            normalized.append(nad)
        if len(normalized) >= max_ads:
            break

    return normalized
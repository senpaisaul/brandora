"""Analyze ads: copy (text-only) + visual (vision) via Claude Haiku 4.5."""
from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from app.config import settings
from app.llm.client import extract_structured
from app.llm.prompts import COPY_ANALYSIS_SYSTEM, VISUAL_ANALYSIS_SYSTEM
from app.models import Ad, CopyAnalysis, VisualAnalysis


def _encode_image(path: str) -> tuple[str, str]:
    """Read an image file and return (media_type, base64_data)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    ext = p.suffix.lower().lstrip(".")
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
    return media_type, data


def analyze_copy_sync(ad: Ad) -> CopyAnalysis:
    """Synchronous copy analysis — text only."""
    user_text = (
        f"Primary text: {ad.primary_text or '(none)'}\n"
        f"Headline: {ad.headline or '(none)'}\n"
        f"CTA: {ad.cta_text or '(none)'}"
    )
    return extract_structured(
        model=settings.model_haiku,
        system=COPY_ANALYSIS_SYSTEM,
        user_content=user_text,
        response_schema=CopyAnalysis,
        max_tokens=1000,
    )


def analyze_visual_sync(ad: Ad) -> VisualAnalysis | None:
    """Synchronous visual analysis — first cached image only."""
    if not ad.local_image_paths:
        return None

    media_type, b64 = _encode_image(ad.local_image_paths[0])

    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        },
        {
            "type": "text",
            "text": (
                f"Analyze this Meta ad creative from the brand '{ad.page_name or 'unknown'}'. "
                f"The ad format is: {ad.format}."
            ),
        },
    ]

    return extract_structured(
        model=settings.model_haiku,
        system=VISUAL_ANALYSIS_SYSTEM,
        user_content=content,
        response_schema=VisualAnalysis,
        max_tokens=1000,
    )


def _derive_tags(copy: CopyAnalysis, visual: VisualAnalysis | None) -> list[str]:
    """Distill copy+visual into short, UI-friendly filter tags."""
    tags: list[str] = [copy.messaging_angle]
    if visual:
        tags.append(f"style:{visual.style}")
        tags.append(f"product:{visual.product_visibility}")
        if visual.has_people:
            tags.append("has-people")
        if visual.has_text_overlay:
            tags.append("text-overlay")
        if visual.ugc_looking:
            tags.append("ugc")
    return tags


async def analyze_ad(ad: Ad) -> tuple[CopyAnalysis, VisualAnalysis | None, list[str]]:
    """Run copy + visual analysis concurrently for one ad."""
    copy_task = asyncio.to_thread(analyze_copy_sync, ad)
    visual_task = asyncio.to_thread(analyze_visual_sync, ad)
    copy, visual = await asyncio.gather(copy_task, visual_task)
    tags = _derive_tags(copy, visual)
    return copy, visual, tags


async def analyze_ads_bulk(ads: list[Ad]) -> list[tuple[int, CopyAnalysis, VisualAnalysis | None, list[str]]]:
    """Analyze many ads concurrently. Returns (ad_id, copy, visual, tags) tuples."""
    tasks = [analyze_ad(ad) for ad in ads]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = []
    for ad, result in zip(ads, results):
        if isinstance(result, Exception):
            print(f"  ⚠  Failed to analyze ad {ad.id}: {result}")
            continue
        copy, visual, tags = result
        output.append((ad.id, copy, visual, tags))
    return output
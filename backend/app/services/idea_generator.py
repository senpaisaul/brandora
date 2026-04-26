"""Generate grounded ad ideas for a brand using Claude Opus 4.7."""
from __future__ import annotations

from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.llm.client import extract_structured
from app.llm.prompts import IDEA_GENERATION_SYSTEM, format_ad_for_prompt
from app.models import Ad, AdAnalysis, AdIdeaPayload, Brand, Competitor


class IdeaPair(BaseModel):
    """Opus returns two ideas as explicit named fields — flatter schema than a list
    of nested models, which Opus 4.7 occasionally mishandles via tool use."""
    idea_1: AdIdeaPayload
    idea_2: AdIdeaPayload


def _build_corpus_block(session: Session, brand_id: int) -> str:
    competitors = list(session.exec(select(Competitor).where(Competitor.brand_id == brand_id)).all())
    ads_by_competitor: dict[str, list[tuple[Ad, AdAnalysis | None]]] = {}

    for comp in competitors:
        ads = list(session.exec(select(Ad).where(Ad.competitor_id == comp.id)).all())
        paired: list[tuple[Ad, AdAnalysis | None]] = []
        for ad in ads:
            analysis = session.exec(
                select(AdAnalysis).where(AdAnalysis.ad_id == ad.id)
            ).first()
            paired.append((ad, analysis))
        ads_by_competitor[comp.name] = paired

    blocks: list[str] = []
    for comp_name, pairs in ads_by_competitor.items():
        blocks.append(f"\n=== Competitor: {comp_name} ({len(pairs)} ads) ===")
        for ad, analysis in pairs:
            blocks.append(format_ad_for_prompt(
                ad_id=ad.id,
                competitor_name=comp_name,
                format=ad.format,
                primary_text=ad.primary_text,
                headline=ad.headline,
                cta=ad.cta_text,
                copy_analysis=analysis.copy_analysis if analysis else None,
                visual_analysis=analysis.visual_analysis if analysis else None,
            ))

    return "\n".join(blocks)


def _build_brand_block(brand: Brand) -> str:
    profile = brand.profile or {}
    lines = [
        f"Brand name: {brand.name}",
        f"URL: {brand.url}",
        f"Product category: {profile.get('product_category', 'unknown')}",
        f"Positioning: {profile.get('positioning', 'unknown')}",
        f"Tone of voice: {profile.get('tone_of_voice', 'unknown')}",
        f"Target audience: {profile.get('target_audience', 'unknown')}",
    ]
    vps = profile.get("value_propositions") or []
    if vps:
        lines.append("Value propositions:")
        for vp in vps:
            lines.append(f"  - {vp}")
    claims = profile.get("notable_claims") or []
    if claims:
        lines.append("Notable claims:")
        for c in claims:
            lines.append(f"  - {c}")
    return "\n".join(lines)


def generate_ideas(session: Session, brand_id: int) -> list[AdIdeaPayload]:
    """Generate 2 grounded ad ideas for a brand. Uses Claude Opus 4.7."""
    brand = session.get(Brand, brand_id)
    if not brand:
        raise ValueError(f"Brand {brand_id} not found")

    brand_block = _build_brand_block(brand)
    corpus_block = _build_corpus_block(session, brand_id)

    user_message = (
        f"BRAND PROFILE\n"
        f"=============\n"
        f"{brand_block}\n\n"
        f"COMPETITOR AD CORPUS\n"
        f"====================\n"
        f"{corpus_block}\n\n"
        f"Generate exactly 2 distinct ad ideas for this brand, grounded in the competitor corpus above. "
        f"Return them as idea_1 and idea_2. Each idea must reference at least 2 real ad_ids "
        f"in `inspired_by_ad_ids`, and the two ideas should draw on different competitor angles."
    )

    result = extract_structured(
        model=settings.model_opus,
        system=IDEA_GENERATION_SYSTEM,
        user_content=user_message,
        response_schema=IdeaPair,
        max_tokens=3000,
    )

    return [result.idea_1, result.idea_2]
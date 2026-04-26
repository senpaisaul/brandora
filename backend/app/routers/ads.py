"""Ad analysis endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Ad, AdAnalysis, Competitor
from app.services.ad_analyzer import analyze_ad, analyze_ads_bulk

router = APIRouter(prefix="/ads", tags=["ads"])


@router.post("/{ad_id}/analyze")
async def analyze_single_ad(ad_id: int, session: Session = Depends(get_session)) -> AdAnalysis:
    """Analyze one ad (copy + visual). Idempotent — upserts on existing analysis."""
    ad = session.get(Ad, ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    copy, visual, tags = await analyze_ad(ad)

    existing = session.exec(select(AdAnalysis).where(AdAnalysis.ad_id == ad_id)).first()
    if existing:
        existing.copy_analysis = copy.model_dump()
        existing.visual_analysis = visual.model_dump() if visual else None
        existing.tags = tags
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    analysis = AdAnalysis(
        ad_id=ad_id,
        copy_analysis=copy.model_dump(),
        visual_analysis=visual.model_dump() if visual else None,
        tags=tags,
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


@router.post("/analyze-all/{competitor_id}")
async def analyze_all_ads_for_competitor(
    competitor_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Analyze every ad for one competitor concurrently."""
    comp = session.get(Competitor, competitor_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    ads = list(session.exec(select(Ad).where(Ad.competitor_id == competitor_id)).all())
    if not ads:
        return {"competitor_id": competitor_id, "analyzed": 0}

    results = await analyze_ads_bulk(ads)

    for ad_id, copy, visual, tags in results:
        existing = session.exec(select(AdAnalysis).where(AdAnalysis.ad_id == ad_id)).first()
        if existing:
            existing.copy_analysis = copy.model_dump()
            existing.visual_analysis = visual.model_dump() if visual else None
            existing.tags = tags
            session.add(existing)
        else:
            session.add(AdAnalysis(
                ad_id=ad_id,
                copy_analysis=copy.model_dump(),
                visual_analysis=visual.model_dump() if visual else None,
                tags=tags,
            ))

    session.commit()
    return {
        "competitor_id": competitor_id,
        "competitor_name": comp.name,
        "analyzed": len(results),
        "ad_ids": [r[0] for r in results],
    }


@router.get("/{ad_id}/analysis")
def get_ad_analysis(ad_id: int, session: Session = Depends(get_session)) -> AdAnalysis:
    """Fetch the analysis for one ad."""
    analysis = session.exec(select(AdAnalysis).where(AdAnalysis.ad_id == ad_id)).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis yet for this ad")
    return analysis
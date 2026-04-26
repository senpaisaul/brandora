"""Competitor endpoints — scrape ads on create."""
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlmodel import Session, select

from app.db import get_session
from app.models import Ad, Brand, Competitor
from app.services.ad_scraper import scrape_competitor
router = APIRouter(prefix="/competitors", tags=["competitors"])


class CreateCompetitorRequest(BaseModel):
    brand_id: int
    name: str
    facebook_url: HttpUrl


@router.post("")
def create_competitor(
    payload: CreateCompetitorRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Create a competitor, scrape recent image/carousel ads, persist them."""
    brand = session.get(Brand, payload.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    comp = Competitor(brand_id=payload.brand_id, name=payload.name)
    session.add(comp)
    session.commit()
    session.refresh(comp)

    ads_normalized = scrape_competitor(str(payload.facebook_url), max_ads=6, results_limit=15)

    saved_ids: list[int] = []
    for nad in ads_normalized:
        ad = Ad(
            competitor_id=comp.id,
            meta_ad_id=nad.meta_ad_id,
            format=nad.format,
            creative_urls=nad.creative_urls,
            local_image_paths=nad.local_image_paths,
            primary_text=nad.primary_text,
            headline=nad.headline,
            cta_text=nad.cta_text,
            page_name=nad.page_name,
            raw_payload=nad.raw_payload,
        )
        session.add(ad)
        session.commit()
        session.refresh(ad)
        saved_ids.append(ad.id)

    return {
        "competitor_id": comp.id,
        "competitor_name": comp.name,
        "ads_scraped": len(saved_ids),
        "ad_ids": saved_ids,
    }

@router.get("")
def list_competitors(
    brand_id: int | None = None,
    session: Session = Depends(get_session),
) -> list[Competitor]:
    """List all competitors, optionally filtered by brand_id."""
    stmt = select(Competitor)
    if brand_id is not None:
        stmt = stmt.where(Competitor.brand_id == brand_id)
    return list(session.exec(stmt).all())
    
@router.get("/{competitor_id}/ads")
def list_competitor_ads(competitor_id: int, session: Session = Depends(get_session)) -> list[Ad]:
    return list(session.exec(select(Ad).where(Ad.competitor_id == competitor_id)).all())

@router.delete("/{competitor_id}/ads", status_code=status.HTTP_204_NO_CONTENT)
def delete_competitor_ads(competitor_id: int, session: Session = Depends(get_session)) -> None:
    """Delete all ads for a competitor. Also removes their image cache directories."""
    ads = list(session.exec(select(Ad).where(Ad.competitor_id == competitor_id)).all())
    for ad in ads:
        # Also kill the image cache folder
        if ad.meta_ad_id:
            cache_dir = Path(f"cache/images/{ad.meta_ad_id}")
            if cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
        session.delete(ad)
    session.commit()

@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competitor(competitor_id: int, session: Session = Depends(get_session)) -> None:
    """Delete a competitor and all their ads + image cache."""
    comp = session.get(Competitor, competitor_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")

    # Cascade: delete ads + their caches first
    ads = list(session.exec(select(Ad).where(Ad.competitor_id == competitor_id)).all())
    for ad in ads:
        if ad.meta_ad_id:
            cache_dir = Path(f"cache/images/{ad.meta_ad_id}")
            if cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
        session.delete(ad)

    session.delete(comp)
    session.commit()
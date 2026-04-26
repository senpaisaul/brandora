"""Ad idea generation endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import AdIdea, Brand
from app.services.idea_generator import generate_ideas

router = APIRouter(prefix="/brands", tags=["ideas"])


@router.post("/{brand_id}/generate-ideas")
def generate_brand_ideas(brand_id: int, session: Session = Depends(get_session)) -> list[AdIdea]:
    """Generate 2 grounded ad ideas for a brand. Appends to history — never replaces."""
    brand = session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    ideas = generate_ideas(session, brand_id)

    # Insert all rows first, commit once, then refresh at the end
    rows = [AdIdea(brand_id=brand_id, payload=idea.model_dump()) for idea in ideas]
    for row in rows:
        session.add(row)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


@router.get("/{brand_id}/ideas")
def list_brand_ideas(brand_id: int, session: Session = Depends(get_session)) -> list[AdIdea]:
    """List all ideas ever generated for this brand, newest first."""
    brand = session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    return list(session.exec(
        select(AdIdea)
        .where(AdIdea.brand_id == brand_id)
        .order_by(AdIdea.created_at.desc())
    ).all())
"""Brand endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlmodel import Session, select

from app.db import get_session
from app.models import Brand
from app.services.brand_profiler import profile_brand

router = APIRouter(prefix="/brands", tags=["brands"])


class CreateBrandRequest(BaseModel):
    name: str
    url: HttpUrl


@router.post("")
def create_brand(payload: CreateBrandRequest, session: Session = Depends(get_session)) -> Brand:
    """Create a brand, scrape its website, and attach the extracted profile."""
    profile = profile_brand(payload.name, str(payload.url))
    brand = Brand(
        name=payload.name,
        url=str(payload.url),
        profile=profile.model_dump(),
    )
    session.add(brand)
    session.commit()
    session.refresh(brand)
    return brand


@router.get("")
def list_brands(session: Session = Depends(get_session)) -> list[Brand]:
    return list(session.exec(select(Brand)).all())


@router.get("/{brand_id}")
def get_brand(brand_id: int, session: Session = Depends(get_session)) -> Brand:
    brand = session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


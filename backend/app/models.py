"""SQLModel tables + the Pydantic schemas stored inside JSON columns.

Design note: JSON columns use explicit Pydantic nested schemas (not loose dicts)
so the data shape is self-documenting and LLM outputs are validated on write.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field as PydField
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Nested Pydantic schemas (stored as JSON inside SQLModel rows)
# ---------------------------------------------------------------------------

class BrandProfile(BaseModel):
    """LLM-extracted profile of a brand's website."""
    product_category: str
    positioning: str
    tone_of_voice: str
    target_audience: str
    value_propositions: list[str]
    notable_claims: list[str] = PydField(default_factory=list)


class CopyAnalysis(BaseModel):
    """Analysis of an ad's text — hook, CTA, messaging angle."""
    hook: str
    cta: Optional[str] = None
    messaging_angle: str  # e.g. "pain_point", "aspiration", "social_proof", "offer", "urgency"
    emotional_tone: str
    key_phrases: list[str] = PydField(default_factory=list)


class VisualAnalysis(BaseModel):
    """Vision-model analysis of an ad's creative image(s)."""
    style: str  # e.g. "minimal", "bold", "lifestyle", "product-shot", "before-after"
    has_people: bool
    has_text_overlay: bool
    ugc_looking: bool  # True = feels user-generated, False = produced
    product_visibility: str  # "prominent", "subtle", "absent"
    dominant_colors: list[str] = PydField(default_factory=list)
    description: str  # 1-2 sentence visual description


class AdIdeaPayload(BaseModel):
    """A generated ad idea, adapted for the user's brand."""
    hook: str
    creative_concept: str
    format: str  # "single_image" or "carousel"
    brand_fit_rationale: str
    inspired_by_ad_ids: list[int] = PydField(default_factory=list)


# ---------------------------------------------------------------------------
# SQLModel tables
# ---------------------------------------------------------------------------

class Brand(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: str
    profile: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Competitor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    brand_id: int = Field(foreign_key="brand.id", index=True)
    name: str


class Ad(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    competitor_id: int = Field(foreign_key="competitor.id", index=True)
    meta_ad_id: Optional[str] = Field(default=None, index=True)
    format: str  # "image" or "carousel"
    creative_urls: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    local_image_paths: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    primary_text: Optional[str] = None
    headline: Optional[str] = None
    cta_text: Optional[str] = None
    page_name: Optional[str] = None
    raw_payload: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class AdAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ad_id: int = Field(foreign_key="ad.id", index=True, unique=True)
    copy_analysis: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    visual_analysis: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AdIdea(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    brand_id: int = Field(foreign_key="brand.id", index=True)
    payload: dict = Field(sa_column=Column(JSON))  # serialized AdIdeaPayload
    created_at: datetime = Field(default_factory=datetime.utcnow)
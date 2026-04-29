from datetime import date, datetime

from pydantic import BaseModel, Field


class TenderBase(BaseModel):
    company: str
    title: str
    tender_number: str
    sector: str
    location: str
    closing_date: date
    source_portal: str
    source_url: str
    matched_keywords: list[str] = Field(default_factory=list)
    relevance_score: float = 0
    status: str = "Review"
    ai_summary: str = ""
    bid_recommendation: str = "Review"


class TenderResponse(TenderBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class KeywordCreate(BaseModel):
    value: str
    weight: float = 1.0


class KeywordResponse(KeywordCreate):
    id: int

    class Config:
        from_attributes = True


class SourceCreate(BaseModel):
    name: str
    url: str


class SourceResponse(SourceCreate):
    id: int

    class Config:
        from_attributes = True

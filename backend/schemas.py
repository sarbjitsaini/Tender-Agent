from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenderBase(BaseModel):
    company: str
    title: str
    tender_number: str
    sector: str
    location: str
    closing_date: str
    source_portal: str
    source_url: str
    matched_keywords: list[str] = Field(default_factory=list)
    relevance_score: float
    status: str
    ai_summary: str
    bid_recommendation: str


class TenderCreate(TenderBase):
    pass


class TenderOut(TenderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class KeywordBase(BaseModel):
    term: str
    weight: float = 1


class KeywordCreate(KeywordBase):
    pass


class KeywordOut(KeywordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class SourceBase(BaseModel):
    name: str
    url: str
    source_type: str = "Public"
    is_active: bool = True


class SourceCreate(SourceBase):
    pass


class SourceOut(SourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ScanResult(BaseModel):
    scanned: int
    created: int
    updated: int
    tenders: list[TenderOut]

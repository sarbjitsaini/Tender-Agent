from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text

from database import Base


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), nullable=False)
    title = Column(String(500), nullable=False)
    tender_number = Column(String(100), nullable=False, unique=True)
    sector = Column(String(50), nullable=False)
    location = Column(String(255), nullable=False)
    closing_date = Column(Date, nullable=False)
    source_portal = Column(String(255), nullable=False)
    source_url = Column(String(500), nullable=False)
    matched_keywords = Column(Text, nullable=False, default="")
    relevance_score = Column(Float, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="Review")
    ai_summary = Column(Text, nullable=False, default="")
    bid_recommendation = Column(String(100), nullable=False, default="Review")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(String(255), nullable=False, unique=True)
    weight = Column(Float, nullable=False, default=1.0)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    url = Column(String(500), nullable=False)

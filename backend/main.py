import json
import logging
from collections.abc import Sequence

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import models
from database import Base, SessionLocal, engine, get_db
from email_alerts import send_high_relevance_alerts, start_daily_summary_scheduler
from schemas import KeywordCreate, KeywordOut, ScanResult, SourceCreate, SourceOut, TenderOut
from scoring import DEFAULT_KEYWORD_WEIGHTS, weights_from_keywords
from scraper import fetch_live_tenders

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Oil & Gas Tender Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_defaults(db)
    start_daily_summary_scheduler(SessionLocal)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "oil-gas-tender-agent"}


@app.get("/tenders", response_model=list[TenderOut])
def get_tenders(db: Session = Depends(get_db)):
    tenders = db.scalars(select(models.Tender).order_by(models.Tender.relevance_score.desc())).all()
    return [serialize_tender(tender) for tender in tenders]


@app.get("/tenders/{tender_id}", response_model=TenderOut)
def get_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.get(models.Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    return serialize_tender(tender)


@app.post("/scan", response_model=ScanResult)
def scan_tenders(db: Session = Depends(get_db)):
    keyword_weights = weights_from_keywords(db.scalars(select(models.Keyword)).all())
    scraped_tenders = fetch_live_tenders(keyword_weights)
    db.execute(delete(models.Tender))
    saved_tenders = []

    for tender_data in scraped_tenders:
        payload = tender_payload_for_db(tender_data)
        saved_tender = models.Tender(**payload)
        db.add(saved_tender)
        saved_tenders.append(saved_tender)

    db.commit()
    for tender in saved_tenders:
        db.refresh(tender)

    serialized_tenders = [serialize_tender(tender) for tender in saved_tenders]
    send_high_relevance_alerts(serialized_tenders)

    return {
        "scanned": len(scraped_tenders),
        "created": len(saved_tenders),
        "updated": 0,
        "tenders": serialized_tenders,
    }


@app.get("/keywords", response_model=list[KeywordOut])
def get_keywords(db: Session = Depends(get_db)):
    return db.scalars(select(models.Keyword).order_by(models.Keyword.weight.desc(), models.Keyword.term)).all()


@app.post("/keywords", response_model=KeywordOut, status_code=status.HTTP_201_CREATED)
def create_keyword(keyword: KeywordCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(models.Keyword).where(models.Keyword.term == keyword.term))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Keyword already exists")

    db_keyword = models.Keyword(**keyword.model_dump())
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)
    return db_keyword


@app.get("/sources", response_model=list[SourceOut])
def get_sources(db: Session = Depends(get_db)):
    return db.scalars(select(models.Source).order_by(models.Source.name)).all()


@app.post("/sources", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def create_source(source: SourceCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(models.Source).where(models.Source.name == source.name))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Source already exists")

    db_source = models.Source(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source


@app.post("/tenders/{tender_id}/mark-bid-review", response_model=TenderOut)
def mark_bid_review(tender_id: int, db: Session = Depends(get_db)):
    tender = db.get(models.Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")

    tender.status = "High Priority"
    tender.bid_recommendation = "Bid Review"
    db.commit()
    db.refresh(tender)
    return serialize_tender(tender)


def seed_defaults(db: Session):
    for term, weight in DEFAULT_KEYWORD_WEIGHTS.items():
        exists = db.scalar(select(models.Keyword).where(models.Keyword.term == term))
        if exists is None:
            db.add(models.Keyword(term=term, weight=weight))
        else:
            exists.weight = weight

    default_sources = [
        ("CPPP", "https://eprocure.gov.in/eprocure/app?page=FrontEndLatestActiveTendersOrgwise&service=page", "Public"),
        ("ONGC eProcurement", "https://tenders.ongc.co.in/", "Public"),
        ("Oil India National", "https://www.oil-india.com/tender-list/63", "Public"),
        ("Oil India Global", "https://www.oil-india.com/tender-list/64", "Public"),
        ("Oil India MSE", "https://www.oil-india.com/tender-list/265", "Public"),
        ("GAIL Tenders", "https://gailtenders.in", "Public"),
        ("IOCL Tenders", "https://iocletenders.gov.in", "Public"),
        ("BPCL Tenders", "https://www.bharatpetroleum.in/Tenders/Tenders.aspx", "Public"),
        ("HPCL Tenders", "https://www.hindustanpetroleum.com/tenders", "Public"),
    ]
    for name, url, source_type in default_sources:
        exists = db.scalar(select(models.Source).where(models.Source.name == name))
        if exists is None:
            db.add(models.Source(name=name, url=url, source_type=source_type))
        else:
            exists.url = url
            exists.source_type = source_type

    db.commit()


def tender_payload_for_db(tender_data: dict) -> dict:
    return {
        **tender_data,
        "matched_keywords": json.dumps(tender_data["matched_keywords"]),
    }


def serialize_tender(tender: models.Tender) -> dict:
    data = tender.__dict__.copy()
    data["matched_keywords"] = parse_keywords(tender.matched_keywords)
    return data


def parse_keywords(value: str | Sequence[str]) -> list[str]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [item.strip() for item in value.split(",") if item.strip()]
    return parsed if isinstance(parsed, list) else []

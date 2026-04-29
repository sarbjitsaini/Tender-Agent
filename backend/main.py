from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import Base, engine, get_db
from scoring import priority_from_score, score_tender
from scraper import fetch_mock_tenders
from alerts import send_daily_summary_if_due, send_high_priority_alert

app = FastAPI(title="Oil & Gas Tender Agent API")

Base.metadata.create_all(bind=engine)

DEFAULT_KEYWORDS = [
    {"value": "hot oil circulation", "weight": 4.0},
    {"value": "hot oiling", "weight": 4.0},
    {"value": "HOC", "weight": 2.0},
    {"value": "chemical injection", "weight": 3.0},
    {"value": "chemical dosing", "weight": 3.0},
    {"value": "corrosion inhibitor", "weight": 2.5},
    {"value": "scale inhibitor", "weight": 2.0},
    {"value": "wax removal", "weight": 2.5},
    {"value": "paraffin", "weight": 2.5},
    {"value": "flow assurance", "weight": 2.0},
    {"value": "dosing pump", "weight": 2.0},
    {"value": "Mehsana", "weight": 2.0},
    {"value": "Cambay", "weight": 2.0},
    {"value": "Ahmedabad", "weight": 1.5},
    {"value": "Gujarat", "weight": 1.0},
]


def ensure_defaults(db: Session):
    if db.query(models.Keyword).count() == 0:
        for item in DEFAULT_KEYWORDS:
            db.add(models.Keyword(value=item["value"], weight=item["weight"]))
    if db.query(models.Source).count() == 0:
        db.add(models.Source(name="ONGC eProc Portal", url="https://example.com/ongc"))
        db.add(models.Source(name="Vendor Procurement Hub", url="https://example.com/cairn"))
    db.commit()


@app.get("/tenders", response_model=list[schemas.TenderResponse])
def get_tenders(db: Session = Depends(get_db)):
    ensure_defaults(db)
    tenders = db.query(models.Tender).order_by(models.Tender.created_at.desc()).all()
    return [serialize_tender(t) for t in tenders]


@app.get("/tenders/{tender_id}", response_model=schemas.TenderResponse)
def get_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return serialize_tender(tender)


@app.post("/scan", response_model=list[schemas.TenderResponse])
def scan_tenders(db: Session = Depends(get_db)):
    ensure_defaults(db)
    ingested = []

    for item in fetch_mock_tenders():
        exists = db.query(models.Tender).filter(models.Tender.tender_number == item["tender_number"]).first()
        if exists:
            ingested.append(serialize_tender(exists))
            continue

        matched, relevance = score_tender(item["company"], item["title"], item["location"])
        status, recommendation = priority_from_score(relevance)

        tender = models.Tender(
            **item,
            matched_keywords=",".join(matched),
            relevance_score=relevance,
            status=status,
            bid_recommendation=recommendation,
        )
        db.add(tender)
        db.commit()
        db.refresh(tender)
        serialized = serialize_tender(tender)
        ingested.append(serialized)

        if serialized["relevance_score"] >= 80:
            send_high_priority_alert(serialized)

    send_daily_summary_if_due(ingested)
    return ingested


@app.get("/keywords", response_model=list[schemas.KeywordResponse])
def get_keywords(db: Session = Depends(get_db)):
    ensure_defaults(db)
    return db.query(models.Keyword).order_by(models.Keyword.id.asc()).all()


@app.post("/keywords", response_model=schemas.KeywordResponse)
def add_keyword(payload: schemas.KeywordCreate, db: Session = Depends(get_db)):
    exists = db.query(models.Keyword).filter(models.Keyword.value.ilike(payload.value)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Keyword already exists")

    keyword = models.Keyword(value=payload.value, weight=payload.weight)
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


@app.get("/sources", response_model=list[schemas.SourceResponse])
def get_sources(db: Session = Depends(get_db)):
    ensure_defaults(db)
    return db.query(models.Source).order_by(models.Source.id.asc()).all()


@app.post("/sources", response_model=schemas.SourceResponse)
def add_source(payload: schemas.SourceCreate, db: Session = Depends(get_db)):
    exists = db.query(models.Source).filter(models.Source.name.ilike(payload.name)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Source already exists")

    source = models.Source(name=payload.name, url=payload.url)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@app.post("/tenders/{tender_id}/mark-bid-review", response_model=schemas.TenderResponse)
def mark_bid_review(tender_id: int, db: Session = Depends(get_db)):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    tender.status = "Review"
    tender.bid_recommendation = "Bid Review"
    db.commit()
    db.refresh(tender)
    return serialize_tender(tender)


def serialize_tender(tender: models.Tender):
    return {
        "id": tender.id,
        "company": tender.company,
        "title": tender.title,
        "tender_number": tender.tender_number,
        "sector": tender.sector,
        "location": tender.location,
        "closing_date": tender.closing_date,
        "source_portal": tender.source_portal,
        "source_url": tender.source_url,
        "matched_keywords": [k for k in tender.matched_keywords.split(",") if k],
        "relevance_score": tender.relevance_score,
        "status": tender.status,
        "ai_summary": tender.ai_summary,
        "bid_recommendation": tender.bid_recommendation,
        "created_at": tender.created_at,
    }

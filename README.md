# Oil & Gas Tender Agent

## 1) What this app does
Oil & Gas Tender Agent is a full-stack monitoring dashboard for **AONE Exploration Pvt Ltd**.

It helps teams:
- scan mock/public tender feeds,
- score relevance based on oil & gas service keywords,
- prioritize opportunities (`High Priority`, `Review`, `Low Priority`),
- review tenders in a dashboard,
- send SMTP email alerts for high-priority tenders and daily summaries.

---

## 2) How to install frontend
From repository root:

```bash
npm install
```

Frontend stack:
- React
- Vite
- Tailwind CSS
- lucide-react

---

## 3) How to install backend
From repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Backend stack:
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic

---

## 4) How to run the app
### Start backend (port 8000)
```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Start frontend (port 5173 by default)
In another terminal:
```bash
npm run dev
```

### App flow
- Frontend calls `GET http://localhost:8000/tenders`
- Clicking **Run Scan** triggers `POST http://localhost:8000/scan`, then refreshes tenders list.

---

## 5) How to add tender sources
You can add source metadata through API:

```bash
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{"name":"New Public Source","url":"https://example.com/public-tenders"}'
```

To add actual scraper logic, edit:
- `backend/scraper.py`

Add a new source function returning `list[dict]` with tender fields, then include it in `fetch_mock_tenders()`.

---

## 6) How to add keywords
Add keywords via API:

```bash
curl -X POST http://localhost:8000/keywords \
  -H "Content-Type: application/json" \
  -d '{"value":"well intervention","weight":20}'
```

List current keywords:

```bash
curl http://localhost:8000/keywords
```

---

## 7) How scoring works
Scoring is rule-based (`backend/scoring.py`) and applies:
- **positive signals** (e.g., hot oil circulation, chemical injection, ONGC, GAIL),
- **negative signals** (e.g., civil work, housekeeping, canteen).

Final relevance score is bounded to `0..100`.

Status mapping:
- `score >= 80` → **High Priority**
- `score 50..79` → **Review**
- `score < 50` → **Low Priority**

Email alerts:
- Immediate alert when `relevance_score >= 80`
- Daily summary email (once per day)

SMTP configuration is loaded from `.env` (see `.env.example`).

---

## 8) Legal note
This app must be used only for lawful, authorized access to tender information.

**It must not:**
- bypass CAPTCHA,
- bypass login/authentication,
- scrape restricted/private pages,
- violate terms of service of tender portals.

Only use publicly available pages and approved data access methods.

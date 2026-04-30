# Oil & Gas Tender Agent

Oil & Gas Tender Agent monitors public and private oil and gas tender sources for AONE Exploration Pvt Ltd. The app helps identify tenders related to hot oil circulation, hot oiling, chemical injection, chemical dosing, inhibitors, wax removal, paraffin control, flow assurance, dosing pumps, and Gujarat-focused opportunities.

The MVP includes:

- React/Vite/Tailwind dashboard
- FastAPI backend
- SQLite database
- SQLAlchemy models
- Pydantic schemas
- Safe public-page tender scanner
- Keyword-based relevance scoring
- SMTP email alert support

## Frontend Install

From the project root:

```powershell
npm.cmd install
```

The frontend uses:

- React
- Vite
- Tailwind CSS
- lucide-react

## Backend Install

Install Python dependencies from the project root:

```powershell
python -m pip install -r backend\requirements.txt
```

If `python` is not available on PATH, use your local Python executable path.

Create backend environment settings:

```powershell
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env` with SMTP settings only when email alerts should be enabled. Never commit real passwords.

## Run The App

Start the backend:

```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Backend API:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

Start the frontend in another terminal:

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Frontend dashboard:

- http://127.0.0.1:5173

Use the dashboard `Run Scan` button to call `POST /scan`, update SQLite tender records, and refresh the tender list.

## Add Tender Sources

Tender sources are stored through the backend API:

- `GET /sources`
- `POST /sources`

Example:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/sources `
  -ContentType 'application/json' `
  -Body '{"name":"New Public Portal","url":"https://example.com/tenders","source_type":"Public","is_active":true}'
```

Scraper functions live in `backend/scraper.py`. Existing safe scraper functions include:

- `scrape_cppp_tenders`
- `scrape_ongc_tenders`
- `scrape_oil_india_tenders`
- `scrape_gail_tenders`
- `scrape_iocl_tenders`
- `scrape_bpcl_tenders`
- `scrape_hpcl_tenders`
- `scrape_private_vendor_portals`

Each scraper returns a list of tender dictionaries. Scrapers should only read publicly available pages and must return an empty list if access fails or the page appears restricted.

## Add Keywords

Keywords are stored through the backend API:

- `GET /keywords`
- `POST /keywords`

Example:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/keywords `
  -ContentType 'application/json' `
  -Body '{"term":"well stimulation","weight":30}'
```

Default keyword weights are defined in `backend/scoring.py`. On backend startup, built-in keyword weights are refreshed in SQLite. Custom keywords added through the API remain available.

## Scoring

The scoring engine matches tender text against weighted keywords in `backend/scoring.py`.

Positive examples:

- `hot oil circulation`: +60
- `hot oiling`: +60
- `chemical injection`: +50
- `chemical dosing`: +45
- `flow assurance`: +35
- `Mehsana`: +25
- `ONGC`: +25

Negative examples:

- `civil work`: -40
- `housekeeping`: -40
- `furniture`: -30
- `painting`: -25
- `canteen`: -40
- `security service`: -40

Final scores are capped between `0` and `100`.

Status logic:

- `score >= 80`: High Priority
- `score 50 to 79`: Review
- `score below 50`: Low Priority

Immediate email alerts are sent after scans when `relevance_score >= ALERT_SCORE_THRESHOLD`, usually `80`, and SMTP alerts are enabled in `backend\.env`.

## Legal And Access Note

This app must not bypass CAPTCHA, login, paywalls, session controls, robots restrictions, or restricted tender portals.

Scrapers must:

- Use only publicly available pages
- Skip CAPTCHA pages
- Skip login-gated pages
- Skip restricted or unauthorized pages
- Log errors and continue
- Avoid any attempt to defeat access controls

For restricted tender portals, use official APIs, authorized vendor access, manual upload, or approved integrations instead of scraping.

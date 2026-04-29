from datetime import date
import logging

logger = logging.getLogger(__name__)


def _safe_collect(source_name: str, fn):
    try:
        return fn()
    except Exception as exc:
        logger.exception("Scraper failed for %s: %s", source_name, exc)
        return []


def scrape_cppp() -> list[dict]:
    """Mock parser for publicly listed CPPP opportunities (no login/captcha bypass)."""
    return [
        {
            "company": "CPPP",
            "title": "Flow Assurance Chemical Dosing Services",
            "tender_number": "CPPP-2026-FA-001",
            "sector": "Public",
            "location": "Gujarat",
            "closing_date": date(2026, 5, 22),
            "source_portal": "CPPP",
            "source_url": "https://eprocure.gov.in/",
            "ai_summary": "Publicly listed flow assurance services requirement from CPPP.",
        }
    ]


def scrape_ongc() -> list[dict]:
    return [
        {
            "company": "ONGC",
            "title": "Hot Oil Circulation Services for North Gujarat Assets",
            "tender_number": "ONGC-2026-HOC-110",
            "sector": "Public",
            "location": "Mehsana, Gujarat",
            "closing_date": date(2026, 5, 10),
            "source_portal": "ONGC eProc Portal",
            "source_url": "https://ongcletenders.net/",
            "ai_summary": "Public tender for paraffin mitigation via hot oil circulation.",
        }
    ]


def scrape_oil_india() -> list[dict]:
    return [
        {
            "company": "Oil India",
            "title": "Chemical Injection Package for Onshore Wells",
            "tender_number": "OIL-2026-CI-022",
            "sector": "Public",
            "location": "Duliajan",
            "closing_date": date(2026, 5, 20),
            "source_portal": "Oil India Tenders",
            "source_url": "https://www.oil-india.com/Tenders",
            "ai_summary": "Publicly listed tender for chemical injection operations.",
        }
    ]


def scrape_gail() -> list[dict]:
    return [
        {
            "company": "GAIL",
            "title": "Corrosion Inhibitor Supply and Dosing Supervision",
            "tender_number": "GAIL-2026-CORR-008",
            "sector": "Public",
            "location": "Ahmedabad, Gujarat",
            "closing_date": date(2026, 5, 19),
            "source_portal": "GAIL eTender",
            "source_url": "https://etender.gail.co.in/",
            "ai_summary": "Public requirement for corrosion inhibitor dosing support.",
        }
    ]


def scrape_iocl() -> list[dict]:
    return []


def scrape_bpcl() -> list[dict]:
    return []


def scrape_hpcl() -> list[dict]:
    return []


def scrape_private_vendor_portals() -> list[dict]:
    return [
        {
            "company": "Private Vendor",
            "title": "Dosing Pump O&M for Cambay Field",
            "tender_number": "PV-2026-DP-301",
            "sector": "Private",
            "location": "Cambay, Gujarat",
            "closing_date": date(2026, 5, 23),
            "source_portal": "Vendor Procurement Hub",
            "source_url": "https://example.com/vendor-portal",
            "ai_summary": "Public listing for dosing pump operations and maintenance services.",
        }
    ]


def fetch_mock_tenders() -> list[dict]:
    """Aggregate safe, public-source scrapers. No login/captcha/restricted bypass logic."""
    all_items = []
    scrapers = [
        ("CPPP", scrape_cppp),
        ("ONGC", scrape_ongc),
        ("Oil India", scrape_oil_india),
        ("GAIL", scrape_gail),
        ("IOCL", scrape_iocl),
        ("BPCL", scrape_bpcl),
        ("HPCL", scrape_hpcl),
        ("Private vendor portals", scrape_private_vendor_portals),
    ]

    for source_name, scraper in scrapers:
        items = _safe_collect(source_name, scraper)
        all_items.extend(items)

    return all_items

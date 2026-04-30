import logging
import hashlib
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from scoring import score_tender

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 12
USER_AGENT = "oil-gas-tender-agent/0.1 public-tender-monitor"

PUBLIC_TENDER_SOURCES = {
    "CPPP": "https://eprocure.gov.in/eprocure/app?page=FrontEndLatestActiveTendersOrgwise&service=page",
    "ONGC": "https://tenders.ongc.co.in/",
    "Oil India National": "https://www.oil-india.com/tender-list/63",
    "Oil India Global": "https://www.oil-india.com/tender-list/64",
    "Oil India MSE": "https://www.oil-india.com/tender-list/265",
    "GAIL": "https://gailtenders.in",
    "IOCL": "https://iocletenders.gov.in",
    "BPCL": "https://www.bharatpetroleum.in/Tenders/Tenders.aspx",
    "HPCL": "https://www.hindustanpetroleum.com/tenders",
}

RESTRICTED_PAGE_MARKERS = (
    "captcha",
    "password",
    "unauthorized",
    "access denied",
    "forbidden",
)

TENDER_TEXT_MARKERS = (
    "tender",
    "e-tender",
    "e tender",
    "procurement",
    "bid",
    "rfq",
    "notice inviting tender",
)


class TenderLinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links = []
        self._current_href = None
        self._current_text = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag != "a":
            return

        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            if href.strip().lower().startswith("javascript:"):
                self._current_href = self.base_url
            else:
                self._current_href = urljoin(self.base_url, href)
            self._current_text = []

    def handle_data(self, data: str):
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str):
        if tag != "a" or not self._current_href:
            return

        title = " ".join(" ".join(self._current_text).split())
        if title and looks_like_tender_text(title) and not is_navigation_text(title):
            self.links.append({"title": title, "url": self._current_href})

        self._current_href = None
        self._current_text = []


class VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lines = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str):
        if self._skip_depth:
            return

        line = " ".join(data.split())
        if line:
            self.lines.append(line)


def fetch_live_tenders(keyword_weights: dict[str, float] | None = None) -> list[dict]:
    return enrich_tenders(scrape_all_public_sources(), keyword_weights)


def scrape_cppp_tenders() -> list[dict]:
    return scrape_public_tender_page(
        company="Central Public Procurement Portal",
        source_portal="CPPP",
        source_url=PUBLIC_TENDER_SOURCES["CPPP"],
        sector="Public",
    )


def scrape_ongc_tenders() -> list[dict]:
    return scrape_public_tender_page(
        company="ONGC",
        source_portal="ONGC eProcurement",
        source_url=PUBLIC_TENDER_SOURCES["ONGC"],
        sector="Public",
    )


def scrape_oil_india_tenders() -> list[dict]:
    tenders = []
    for source_name in ("Oil India National", "Oil India Global", "Oil India MSE"):
        tenders.extend(
            scrape_public_tender_page(
                company="Oil India Limited",
                source_portal=source_name,
                source_url=PUBLIC_TENDER_SOURCES[source_name],
                sector="Public",
            )
        )
    return tenders


def scrape_gail_tenders() -> list[dict]:
    return scrape_public_tender_page(
        company="GAIL",
        source_portal="GAIL Tenders",
        source_url=PUBLIC_TENDER_SOURCES["GAIL"],
        sector="Public",
    )


def scrape_iocl_tenders() -> list[dict]:
    return scrape_public_tender_page(
        company="IndianOil",
        source_portal="IOCL Tenders",
        source_url=PUBLIC_TENDER_SOURCES["IOCL"],
        sector="Public",
    )


def scrape_bpcl_tenders() -> list[dict]:
    return scrape_public_tender_page(
        company="BPCL",
        source_portal="BPCL Tenders",
        source_url=PUBLIC_TENDER_SOURCES["BPCL"],
        sector="Public",
    )


def scrape_hpcl_tenders() -> list[dict]:
    return scrape_public_tender_page(
        company="HPCL",
        source_portal="HPCL Tenders",
        source_url=PUBLIC_TENDER_SOURCES["HPCL"],
        sector="Public",
    )


def scrape_private_vendor_portals(portal_urls: list[str] | None = None) -> list[dict]:
    tenders = []
    for index, portal_url in enumerate(portal_urls or []):
        tenders.extend(
            scrape_public_tender_page(
                company="Private Vendor Portal",
                source_portal=f"Private Vendor Portal {index + 1}",
                source_url=portal_url,
                sector="Private",
            )
        )
    return tenders


def scrape_all_public_sources(private_portal_urls: list[str] | None = None) -> list[dict]:
    scrapers = [
        scrape_cppp_tenders,
        scrape_ongc_tenders,
        scrape_oil_india_tenders,
        scrape_gail_tenders,
        scrape_iocl_tenders,
        scrape_bpcl_tenders,
        scrape_hpcl_tenders,
    ]

    tenders = []
    for scraper in scrapers:
        try:
            tenders.extend(scraper())
        except Exception:
            logger.exception("Scraper failed: %s", scraper.__name__)

    try:
        tenders.extend(scrape_private_vendor_portals(private_portal_urls))
    except Exception:
        logger.exception("Private vendor portal scraper failed")

    return tenders


def scrape_public_tender_page(company: str, source_portal: str, source_url: str, sector: str) -> list[dict]:
    try:
        html = fetch_public_html(source_url)
        if not html:
            return []

        parser = TenderLinkParser(source_url)
        parser.feed(html)
        tenders = [
            build_scraped_tender(
                company=company,
                title=link["title"],
                sector=sector,
                source_portal=source_portal,
                source_url=link["url"],
            )
            for link in parser.links[:25]
        ]
        tenders.extend(extract_text_tenders(html, company, sector, source_portal, source_url, limit=25))
        return dedupe_tenders(tenders)[:25]
    except Exception:
        logger.exception("Failed to scrape public source: %s", source_portal)
        return []


def fetch_public_html(url: str) -> str | None:
    request = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                logger.info("Skipping non-HTML public page: %s", final_url)
                return None

            html = response.read(750_000).decode("utf-8", errors="ignore")
            if is_restricted_page(final_url, html):
                logger.warning("Skipping restricted or login/CAPTCHA page: %s", final_url)
                return None

            return html
    except HTTPError as exc:
        logger.warning("HTTP error scraping %s: %s", url, exc)
    except URLError as exc:
        logger.warning("Network error scraping %s: %s", url, exc)
    except TimeoutError:
        logger.warning("Timeout scraping %s", url)

    return None


def build_scraped_tender(company: str, title: str, sector: str, source_portal: str, source_url: str) -> dict:
    return {
        "company": company,
        "title": title,
        "tender_number": stable_tender_number(source_portal, title, source_url),
        "sector": sector,
        "location": "Not specified",
        "closing_date": "",
        "source_portal": source_portal,
        "source_url": source_url,
        "matched_keywords": [],
        "relevance_score": 0,
        "status": "Low Priority",
        "ai_summary": "Public tender listing found. Details should be reviewed on the source portal.",
        "bid_recommendation": "Review",
    }


def extract_text_tenders(
    html: str,
    company: str,
    sector: str,
    source_portal: str,
    source_url: str,
    limit: int,
) -> list[dict]:
    parser = VisibleTextParser()
    parser.feed(html)
    tenders = []

    for index, line in enumerate(parser.lines):
        if len(line) < 24 or not looks_like_tender_text(line):
            continue
        if is_navigation_text(line):
            continue

        context = " ".join(parser.lines[index : index + 6])
        title = line[:350]
        tender = build_scraped_tender(
            company=company,
            title=title,
            sector=sector,
            source_portal=source_portal,
            source_url=source_url,
        )
        tender["ai_summary"] = f"Public tender text found on verified source page: {context[:500]}"
        tenders.append(tender)
        if len(tenders) >= limit:
            break

    return tenders


def enrich_tenders(tenders: list[dict], keyword_weights: dict[str, float] | None = None) -> list[dict]:
    enriched = []
    for tender in tenders:
        searchable_text = " ".join(
            [
                tender.get("company", ""),
                tender.get("title", ""),
                tender.get("location", ""),
                tender.get("ai_summary", ""),
                tender.get("source_portal", ""),
            ]
        )
        matched_keywords, relevance_score, status, bid_recommendation = score_tender(
            searchable_text,
            keyword_weights,
        )
        enriched.append(
            {
                **tender,
                "matched_keywords": matched_keywords,
                "relevance_score": relevance_score,
                "status": status,
                "bid_recommendation": bid_recommendation,
            }
        )

    return enriched


def dedupe_tenders(tenders: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for tender in tenders:
        key = (tender["source_portal"], tender["title"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(tender)
    return deduped


def stable_tender_number(source_portal: str, title: str, source_url: str) -> str:
    seed = f"{source_portal}|{title}|{source_url}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12].upper()
    return f"SCRAPED-{digest}"


def looks_like_tender_text(text: str) -> bool:
    normalized_text = text.lower()
    has_tender_marker = any(marker in normalized_text for marker in TENDER_TEXT_MARKERS)
    has_reference_shape = any(char.isdigit() for char in text) and len(text) >= 30
    return has_tender_marker or has_reference_shape


def is_navigation_text(text: str) -> bool:
    normalized_text = text.lower()
    blocked = (
        "(c) 2017 tenders nic",
        "e-tendering of works",
        "latest tender documents issued",
        "plot no.",
        "best viewed",
        "caution:",
        "contact no.",
        "fake website",
        "launches new vendor portal",
        "purchase & procurement",
        "recruitment of",
        "uploaded on",
        "visitors since",
        "archive tender",
        "bid submission closing date",
        "cancelled/retendered",
        "view more",
        "latest tenders",
        "active tenders",
        "national tenders",
        "global tenders",
        "limited tenders",
        "gem tender",
        "e- tender",
        "tender search",
        "tender list",
        "tender's other information",
        "title and ref.no.",
        "tenders by",
        "tenders in archive",
        "tenders status",
        "corrigendum",
        "bid awards",
        "bidder manual kit",
        "click here",
        "contact us",
        "copyright",
        "downloads",
        "e-gas tender",
        "e-gas tenders",
        "eprocurement system government of india",
        "external website",
        "five year procurement plan",
        "for queries related",
        "general terms",
        "home",
        "important notice",
        "last updated",
        "miscellaneous links",
        "notices",
        "notice inviting tender",
        "oil's 5 years procurement plan",
        "oils 5 years procurement plan",
        "pre tender meeting notification",
        "procurement plan",
        "procurement manuals",
        "procurements on nomination basis",
        "registration",
        "screenreader",
        "site map",
        "site best viewed",
        "title and ref",
        "vendor registration",
        "visitor count",
        "welcome",
        "view old tenders",
    )
    bracket_only = normalized_text.startswith("[") and normalized_text.endswith("]")
    url_only = normalized_text.startswith("http://") or normalized_text.startswith("https://")
    generic_single_word = normalized_text in {"procurement", "tender", "tenders"}
    return bracket_only or url_only or generic_single_word or any(marker in normalized_text for marker in blocked)


def is_restricted_page(url: str, html: str) -> bool:
    text = f"{url} {html[:5000]}".lower()
    return any(marker in text for marker in RESTRICTED_PAGE_MARKERS)

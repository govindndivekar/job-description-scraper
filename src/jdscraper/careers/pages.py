from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from jdscraper.ats.detect import detect_ats

LISTING_HINTS = (
    "current opening",
    "current openings",
    "open positions",
    "open position",
    "view jobs",
    "see jobs",
    "all jobs",
    "search jobs",
    "job listings",
    "job listing",
    "job openings",
    "explore jobs",
    "apply now",
    "vacancies",
    "openings",
)
JOB_PATH_HINTS = ("/job/", "/jobs/", "/opening", "/position", "/vacanc")


def _clean(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def page_kind(html: str, url: str = "") -> str:
    hit = detect_ats(url, html or "")
    if hit.kind != "generic":
        return "listings"
    text = (html or "").lower()
    if "application/ld+json" in text and "jobposting" in text:
        return "listings"
    soup = BeautifulSoup(html or "", "html.parser")
    jobish = 0
    for tag in soup.find_all("a", href=True):
        href = str(tag.get("href") or "").lower()
        if any(hint in href for hint in JOB_PATH_HINTS):
            jobish += 1
    if jobish >= 2:
        return "listings"
    if any(hint in text for hint in LISTING_HINTS) and jobish < 2:
        return "marketing"
    if "career" in (url or "").lower() or "career" in text:
        return "marketing"
    return "unknown"


def listings_links_from_html(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    found: list[str] = []
    seen: set[str] = set()
    for tag in soup.find_all("a", href=True):
        href = str(tag.get("href") or "").strip()
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        absolute = _clean(urljoin(base_url, href))
        if not absolute or absolute in seen:
            continue
        blob = f"{href} {tag.get_text(' ', strip=True)}".lower()
        if any(hint in blob for hint in LISTING_HINTS) or any(hint in href.lower() for hint in JOB_PATH_HINTS):
            seen.add(absolute)
            found.append(absolute)
    return found

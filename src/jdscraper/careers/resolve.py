from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

CAREER_HINTS = (
    "career",
    "careers",
    "jobs",
    "job",
    "join-us",
    "joinus",
    "join_us",
    "work-with-us",
    "workwithus",
    "openings",
    "vacancies",
    "opportunities",
)

SKIP_HINTS = (
    "blog",
    "login",
    "signin",
    "sign-in",
    "privacy",
    "cookie",
    "about",
    "press",
    "news",
    "facebook",
    "twitter",
    "linkedin.com/share",
    "instagram",
    "youtube",
)


def _clean(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def career_links_from_html(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    found: list[str] = []
    seen: set[str] = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        absolute = _clean(urljoin(base_url, href))
        if not absolute or absolute in seen:
            continue
        blob = f"{href} {tag.get_text(' ', strip=True)}".lower()
        if any(skip in blob for skip in SKIP_HINTS) and not any(hint in href.lower() for hint in CAREER_HINTS):
            continue
        if any(hint in blob for hint in CAREER_HINTS):
            seen.add(absolute)
            found.append(absolute)
    return found


def guess_career_urls(website: str) -> list[str]:
    parsed = urlparse(website if "://" in website else f"https://{website}")
    origin = f"{parsed.scheme or 'https'}://{parsed.netloc}"
    paths = (
        "/careers",
        "/career",
        "/jobs",
        "/careers/jobs",
        "/en/careers",
        "/en/jobs",
        "/company/careers",
        "/about/careers",
        "/join-us",
        "/joinus",
    )
    return [origin + path for path in paths]

from __future__ import annotations

import json
import os
from urllib.parse import urlparse

from jdscraper.careers.resolve import CAREER_HINTS

PORTAL_HOSTS = (
    "linkedin.com",
    "naukri.com",
    "indeed.com",
    "glassdoor.com",
    "ambitionbox.com",
    "instahyre.com",
    "foundit.in",
    "shine.com",
    "facebook.com",
    "twitter.com",
    "x.com",
)
ATS_HOSTS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "smartrecruiters.com",
    "myworkdayjobs.com",
    "icims.com",
    "successfactors.com",
    "taleo.net",
)


def search_query(name: str, website: str = "") -> str:
    host = urlparse(website).netloc.removeprefix("www.") if website else ""
    if host:
        return f'{name} careers jobs Bangalore site:{host} OR site:greenhouse.io OR site:lever.co'
    return f"{name} official careers jobs Bangalore"


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _is_portal(host: str) -> bool:
    return any(host == bad or host.endswith("." + bad) for bad in PORTAL_HOSTS)


def _is_ats(host: str) -> bool:
    return any(host == good or host.endswith("." + good) for good in ATS_HOSTS)


def _same_site(website: str, url: str) -> bool:
    left = _host(website)
    right = _host(url)
    if not left or not right:
        return False
    return right == left or right.endswith("." + left) or left.endswith("." + right)


def pick_career_hits(name: str, website: str, hits: list[str]) -> list[str]:
    picked: list[str] = []
    seen: set[str] = set()
    for url in hits:
        host = _host(url)
        if not host or _is_portal(host) or url in seen:
            continue
        path = urlparse(url).path.lower()
        careerish = any(hint in path or hint in url.lower() for hint in CAREER_HINTS)
        if _is_ats(host) or (_same_site(website, url) and (careerish or "opening" in url.lower())):
            seen.add(url)
            picked.append(url)
    return picked


def google_cse_urls(payload: dict) -> list[str]:
    urls = []
    for item in payload.get("items") or []:
        link = item.get("link")
        if link:
            urls.append(link)
    return urls


def load_search_secrets() -> tuple[str, str]:
    key = os.environ.get("JDSCRAPER_GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    cx = os.environ.get("JDSCRAPER_GOOGLE_CSE_ID") or os.environ.get("GOOGLE_CSE_ID") or ""
    return key.strip(), cx.strip()


def parse_cse_body(text: str) -> list[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    return google_cse_urls(payload)


def cse_request_url(query: str, key: str, cx: str) -> str:
    from urllib.parse import urlencode

    return "https://www.googleapis.com/customsearch/v1?" + urlencode(
        {"q": query, "key": key, "cx": cx, "num": 5}
    )


def hits_via_google_cse(company, get) -> list[str]:
    key, cx = load_search_secrets()
    if not key or not cx:
        return []
    result = get(cse_request_url(search_query(company.name, company.website), key, cx))
    if getattr(result, "status", 400) >= 400 or not getattr(result, "text", ""):
        return []
    return pick_career_hits(company.name, company.website, parse_cse_body(result.text))

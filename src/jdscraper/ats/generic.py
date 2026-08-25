from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from jdscraper.extract.qa_filter import classify_role
from jdscraper.models import Company, RawJob


def parse_generic_listing(html: str, company: Company, page_url: str) -> list[RawJob]:
    soup = BeautifulSoup(html or "", "html.parser")
    jobs: list[RawJob] = []
    seen: set[str] = set()
    for tag in soup.find_all("a", href=True):
        title = tag.get_text(" ", strip=True)
        if not title or len(title) > 180:
            continue
        href = urljoin(page_url, tag["href"].strip())
        if href in seen:
            continue
        decision = classify_role(title, "", company.city)
        if not decision.keep:
            continue
        seen.add(href)
        jobs.append(
            RawJob(
                source="generic",
                external_id=href,
                title=title,
                company=company.name,
                location=company.city,
                url=href,
                description="",
            )
        )
    return jobs

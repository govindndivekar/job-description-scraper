from __future__ import annotations

from urllib.parse import urljoin, urlparse

from jdscraper.ats.detect import AtsHit, detect_ats
from jdscraper.careers.resolve import career_links_from_html, guess_career_urls
from jdscraper.fetch.polite import PoliteFetcher
from jdscraper.models import Company


def resolve_company(company: Company, fetcher: PoliteFetcher) -> Company:
    if company.ats_kind and company.ats_kind != "generic" and company.career_url:
        return company

    candidates: list[str] = []
    if company.career_url:
        candidates.append(company.career_url)
    if company.website:
        candidates.append(company.website)

    seen: set[str] = set()
    pages_used = 0
    for url in candidates:
        if url in seen:
            continue
        seen.add(url)
        hit = detect_ats(url, "")
        if hit.kind != "generic":
            return _apply_hit(company, hit, url)
        result = fetcher.get(url)
        pages_used += 1
        if result.blocked or result.status >= 400 or not result.text:
            continue
        final_url = result.url or url
        hit = detect_ats(final_url, result.text)
        if hit.kind != "generic":
            return _apply_hit(company, hit, final_url)
        for link in career_links_from_html(result.text, final_url)[:4]:
            hit = detect_ats(link, "")
            if hit.kind != "generic":
                return _apply_hit(company, hit, link)
            if not company.career_url:
                company.career_url = link
                company.ats_kind = company.ats_kind or "generic"

    if company.website and not company.career_url and pages_used < 3:
        for guessed in guess_career_urls(company.website)[:2]:
            if guessed in seen:
                continue
            result = fetcher.get(guessed)
            if result.blocked or result.status >= 400 or not result.text:
                continue
            final_url = result.url or guessed
            hit = detect_ats(final_url, result.text)
            if hit.kind != "generic":
                return _apply_hit(company, hit, final_url)
            company.career_url = final_url
            company.ats_kind = "generic"
            break
    return company


def _apply_hit(company: Company, hit: AtsHit, url: str) -> Company:
    company.career_url = url
    company.ats_kind = hit.kind
    company.ats_slug = hit.slug or company.ats_slug
    company.ats_site = hit.site or company.ats_site
    return company


def origin_of(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def join_url(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))

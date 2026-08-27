from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urljoin, urlparse

from typing import Protocol

from jdscraper.ats.detect import AtsHit, detect_ats
from jdscraper.careers.pages import listings_links_from_html, page_kind
from jdscraper.careers.resolve import career_links_from_html, guess_career_urls
from jdscraper.fetch.polite import FetchResult
from jdscraper.models import Company

SearchFn = Callable[[Company], list[str]]


class _HasGet(Protocol):
    def get(self, url: str) -> FetchResult: ...


def resolve_company(
    company: Company,
    fetcher: _HasGet,
    search: SearchFn | None = None,
    max_pages: int = 6,
) -> Company:
    if company.ats_kind and company.ats_kind != "generic" and company.career_url:
        return company

    original_career = company.career_url
    candidates: list[str] = []
    if company.career_url:
        candidates.append(company.career_url)
    if company.website:
        candidates.append(company.website)

    seen: set[str] = set()
    pages_used = 0

    def consume(urls: list[str]) -> Company | None:
        nonlocal pages_used
        while urls and pages_used < max_pages:
            url = urls.pop(0)
            if url in seen:
                continue
            seen.add(url)
            hit = detect_ats(url, "")
            if hit.kind != "generic":
                return _apply_hit(company, hit, url)
            result = fetcher.get(url)
            pages_used += 1
            if result.blocked:
                continue
            if result.status >= 400 or not result.text:
                if url == original_career:
                    company.career_url = ""
                continue
            final_url = result.url or url
            hit = detect_ats(final_url, result.text)
            if hit.kind != "generic":
                return _apply_hit(company, hit, final_url)
            kind = page_kind(result.text, final_url)
            extra = listings_links_from_html(result.text, final_url)[:4]
            extra += [link for link in career_links_from_html(result.text, final_url)[:4] if link not in extra]
            for link in extra:
                early = detect_ats(link, "")
                if early.kind != "generic":
                    return _apply_hit(company, early, link)
                if link not in seen:
                    urls.append(link)
            if kind == "listings":
                company.career_url = final_url
                company.ats_kind = company.ats_kind or "generic"
                return company
        return None

    found = consume(candidates)
    if found:
        return found

    if search:
        found = consume([url for url in search(company)[:5] if url not in seen])
        if found:
            return found

    if company.website and not company.career_url and pages_used < max_pages:
        guessed = [url for url in guess_career_urls(company.website)[:3] if url not in seen]
        found = consume(guessed)
        if found:
            return found
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

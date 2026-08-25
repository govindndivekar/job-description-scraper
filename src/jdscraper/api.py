from __future__ import annotations

from collections import Counter

from jdscraper.db import JobStore
from jdscraper.models import Company, JobPosting


def job_to_dict(job: JobPosting) -> dict:
    return {
        "id": job.id,
        "role": job.role,
        "company": job.company_name,
        "company_id": job.company_id,
        "years_min": job.years_min,
        "years_max": job.years_max,
        "description": job.description,
        "tech_stack": list(job.tech_stack),
        "domain": job.domain,
        "location": job.location,
        "url": job.url,
        "source": job.source,
        "fetched_at": job.fetched_at,
    }


def company_to_dict(company: Company) -> dict:
    return {
        "id": company.id,
        "name": company.name,
        "website": company.website,
        "career_url": company.career_url,
        "domain": company.domain,
        "city": company.city,
        "ats_kind": company.ats_kind,
        "ats_slug": company.ats_slug,
        "source": company.source,
        "last_crawled_at": company.last_crawled_at,
        "last_status": company.last_status,
    }


def _matches(haystack: str, needle: str) -> bool:
    return needle.lower() in (haystack or "").lower()


def filter_jobs(
    jobs: list[JobPosting],
    *,
    query: str = "",
    domain: str = "",
    company: str = "",
) -> list[JobPosting]:
    out = jobs
    if query:
        out = [
            job
            for job in out
            if _matches(job.role, query)
            or _matches(job.company_name, query)
            or _matches(job.description, query)
            or any(_matches(item, query) for item in job.tech_stack)
        ]
    if domain:
        out = [job for job in out if job.domain.lower() == domain.lower()]
    if company:
        out = [job for job in out if job.company_name.lower() == company.lower()]
    return out


def filter_companies(
    companies: list[Company],
    *,
    query: str = "",
    domain: str = "",
    source: str = "",
    ats: str = "",
) -> list[Company]:
    out = companies
    if query:
        out = [
            company
            for company in out
            if _matches(company.name, query) or _matches(company.website, query)
        ]
    if domain:
        out = [company for company in out if company.domain.lower() == domain.lower()]
    if source:
        out = [company for company in out if company.source.lower() == source.lower()]
    if ats:
        out = [company for company in out if company.ats_kind.lower() == ats.lower()]
    return out


def _count_rows(counter: Counter, *, jobs: Counter | None = None) -> list[dict]:
    rows = []
    for name, count in counter.most_common():
        label = name or "unknown"
        row = {"name": label, "count": count}
        if jobs is not None:
            row["companies"] = count
            row["jobs"] = int(jobs.get(name, 0))
            del row["count"]
        rows.append(row)
    return rows


def catalog_stats(store: JobStore) -> dict:
    companies = store.list_companies()
    jobs = store.list_jobs()
    domain_companies: Counter = Counter(c.domain or "unknown" for c in companies)
    domain_jobs: Counter = Counter(j.domain or "unknown" for j in jobs)
    tech: Counter = Counter()
    for job in jobs:
        tech.update(job.tech_stack)
    crawl_status: Counter = Counter()
    for company in companies:
        crawl_status[company.last_status or "uncrawled"] += 1
    return {
        "companies": len(companies),
        "jobs": len(jobs),
        "with_career": sum(1 for c in companies if c.career_url),
        "with_ats": sum(1 for c in companies if c.ats_kind),
        "crawled": sum(1 for c in companies if c.last_crawled_at),
        "domains": _count_rows(domain_companies, jobs=domain_jobs),
        "sources": _count_rows(Counter(c.source or "unknown" for c in companies)),
        "ats": _count_rows(Counter(c.ats_kind or "none" for c in companies)),
        "tech": [{"name": name, "count": count} for name, count in tech.most_common()],
        "crawl_status": _count_rows(crawl_status),
    }

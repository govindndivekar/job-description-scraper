from __future__ import annotations

from jdscraper.db import JobStore
from jdscraper.extract.fields import extract_fields
from jdscraper.extract.qa_filter import classify_role
from jdscraper.models import Company, JobPosting, RawJob


def ingest_raw_jobs(store: JobStore, company: Company, raw_jobs: list[RawJob]) -> list[JobPosting]:
    kept: list[JobPosting] = []
    for raw in raw_jobs:
        location = raw.location or company.city
        decision = classify_role(raw.title, raw.description, location)
        if not decision.keep:
            continue
        fields = extract_fields(raw.title, raw.description, company.domain)
        posting = JobPosting(
            company_id=company.id,
            company_name=company.name,
            role=raw.title,
            years_min=fields.years_min,
            years_max=fields.years_max,
            description=raw.description,
            tech_stack=fields.tech_stack,
            domain=fields.domain or company.domain,
            location=location,
            url=raw.url,
            source=raw.source,
            external_id=raw.external_id or raw.url,
        )
        kept.append(store.save_job(posting))
    return kept

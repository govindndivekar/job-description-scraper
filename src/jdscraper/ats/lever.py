from __future__ import annotations

from jdscraper.models import RawJob


def parse_lever_jobs(payload: list | dict, company: str) -> list[RawJob]:
    items = payload if isinstance(payload, list) else payload.get("data") or payload.get("postings") or []
    jobs: list[RawJob] = []
    for item in items:
        categories = item.get("categories") or {}
        location = categories.get("location") or item.get("location") or ""
        description = item.get("descriptionPlain") or item.get("description") or ""
        jobs.append(
            RawJob(
                source="lever",
                external_id=str(item.get("id") or ""),
                title=item.get("text") or item.get("title") or "",
                company=company,
                location=location,
                url=item.get("hostedUrl") or item.get("applyUrl") or "",
                description=description,
            )
        )
    return jobs

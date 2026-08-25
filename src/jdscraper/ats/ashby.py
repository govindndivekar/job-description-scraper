from __future__ import annotations

from jdscraper.models import RawJob


def parse_ashby_jobs(payload: dict, company: str) -> list[RawJob]:
    jobs: list[RawJob] = []
    items = payload.get("jobs") or payload.get("jobPostings") or []
    for item in items:
        location = ""
        if isinstance(item.get("location"), str):
            location = item["location"]
        elif isinstance(item.get("address"), dict):
            location = item["address"].get("postalAddress", {}).get("addressLocality") or ""
        description = item.get("descriptionPlain") or ""
        if not description:
            description = item.get("descriptionHtml") or ""
        jobs.append(
            RawJob(
                source="ashby",
                external_id=str(item.get("id") or item.get("jobId") or ""),
                title=item.get("title") or "",
                company=company,
                location=location,
                url=item.get("jobUrl") or item.get("applyUrl") or "",
                description=description,
            )
        )
    return jobs

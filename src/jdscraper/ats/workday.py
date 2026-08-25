from __future__ import annotations

from urllib.parse import urljoin

from jdscraper.models import RawJob


def parse_workday_jobs(payload: dict, company: str, board_url: str) -> list[RawJob]:
    jobs: list[RawJob] = []
    for item in payload.get("jobPostings") or []:
        path = item.get("externalPath") or item.get("externalUrl") or ""
        url = path if path.startswith("http") else urljoin(board_url.rstrip("/") + "/", path.lstrip("/"))
        external = ""
        bullets = item.get("bulletFields") or []
        if bullets:
            external = str(bullets[0])
        if not external:
            external = str(item.get("jobPostingId") or path)
        jobs.append(
            RawJob(
                source="workday",
                external_id=external,
                title=item.get("title") or "",
                company=company,
                location=item.get("locationsText") or item.get("location") or "",
                url=url,
                description=item.get("jobDescription") or item.get("shortDescription") or "",
            )
        )
    return jobs

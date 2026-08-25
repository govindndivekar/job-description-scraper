from __future__ import annotations

import html as html_lib
import re

from jdscraper.models import RawJob

TAG = re.compile(r"<[^>]+>")


def strip_html(value: str) -> str:
    text = html_lib.unescape(value or "")
    text = TAG.sub(" ", text)
    return " ".join(text.split())


def parse_greenhouse_jobs(payload: dict, company: str) -> list[RawJob]:
    jobs: list[RawJob] = []
    for item in payload.get("jobs") or []:
        location = ""
        if isinstance(item.get("location"), dict):
            location = item["location"].get("name") or ""
        if not location:
            offices = item.get("offices") or []
            if offices and isinstance(offices[0], dict):
                location = offices[0].get("location") or offices[0].get("name") or ""
        jobs.append(
            RawJob(
                source="greenhouse",
                external_id=str(item.get("id") or item.get("internal_job_id") or ""),
                title=item.get("title") or "",
                company=company,
                location=location,
                url=item.get("absolute_url") or "",
                description=strip_html(item.get("content") or ""),
            )
        )
    return jobs

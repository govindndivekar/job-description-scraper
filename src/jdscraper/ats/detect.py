from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

GREENHOUSE_BOARD = re.compile(
    r"https?://(?:job-)?boards\.greenhouse\.io/(?:embed/job_board/js\?for=)?([a-zA-Z0-9_-]+)",
    re.I,
)
LEVER_BOARD = re.compile(r"https?://jobs\.lever\.co/([a-zA-Z0-9_-]+)", re.I)
ASHBY_BOARD = re.compile(r"https?://jobs\.ashbyhq\.com/([a-zA-Z0-9_-]+)", re.I)
SMART_BOARD = re.compile(r"https?://jobs\.smartrecruiters\.com/([a-zA-Z0-9_-]+)", re.I)
WORKDAY_BOARD = re.compile(
    r"https?://([a-zA-Z0-9_-]+)\.wd\d+\.myworkdayjobs\.com(?:/[\w-]+)?/([a-zA-Z0-9_-]+)",
    re.I,
)


@dataclass(frozen=True, slots=True)
class AtsHit:
    kind: str
    slug: str | None = None
    site: str | None = None
    career_url: str = ""


def detect_ats(url: str, html: str = "") -> AtsHit:
    blob = f"{url}\n{html}"
    if match := GREENHOUSE_BOARD.search(blob):
        slug = match.group(1)
        if slug.lower() in {"embed", "jobs"}:
            # Prefer the ?for= token already captured, else keep looking.
            for_match = re.search(r"greenhouse\.io/embed/job_board/js\?for=([a-zA-Z0-9_-]+)", blob, re.I)
            if for_match:
                slug = for_match.group(1)
        return AtsHit(kind="greenhouse", slug=slug, career_url=url)
    if match := LEVER_BOARD.search(blob):
        return AtsHit(kind="lever", slug=match.group(1), career_url=url)
    if match := ASHBY_BOARD.search(blob):
        return AtsHit(kind="ashby", slug=match.group(1), career_url=url)
    if match := SMART_BOARD.search(blob):
        return AtsHit(kind="smartrecruiters", slug=match.group(1), career_url=url)
    if match := WORKDAY_BOARD.search(blob):
        return AtsHit(kind="workday", slug=match.group(1), site=match.group(2), career_url=url)
    parsed = urlparse(url)
    if parsed.netloc.endswith("myworkdayjobs.com"):
        parts = [p for p in parsed.path.split("/") if p]
        host = parsed.netloc.split(".")[0]
        site = parts[0] if parts else ""
        return AtsHit(kind="workday", slug=host, site=site, career_url=url)
    return AtsHit(kind="generic", career_url=url)

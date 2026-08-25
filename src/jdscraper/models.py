from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Company:
    name: str
    website: str = ""
    career_url: str = ""
    domain: str = ""
    city: str = "Bengaluru"
    ats_kind: str = ""
    ats_slug: str = ""
    ats_site: str = ""
    source: str = "seed"
    id: int | None = None
    last_crawled_at: str | None = None
    last_status: str = ""


@dataclass(slots=True)
class RawJob:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    description: str = ""


@dataclass(slots=True)
class JobPosting:
    company_name: str
    role: str
    description: str
    url: str
    source: str
    external_id: str
    company_id: int | None = None
    years_min: int | None = None
    years_max: int | None = None
    tech_stack: list[str] = field(default_factory=list)
    domain: str = ""
    location: str = ""
    id: int | None = None
    fetched_at: str | None = None

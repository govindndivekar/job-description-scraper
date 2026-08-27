from __future__ import annotations

import json
from urllib.parse import urlparse

from jdscraper.ats.generic import parse_generic_listing
from jdscraper.ats.ashby import parse_ashby_jobs
from jdscraper.ats.greenhouse import parse_greenhouse_jobs
from jdscraper.ats.lever import parse_lever_jobs
from jdscraper.ats.workday import parse_workday_jobs
from jdscraper.careers.pages import listings_links_from_html
from jdscraper.extract.qa_filter import classify_role
from jdscraper.fetch.polite import FetchResult, PoliteFetcher
from jdscraper.models import Company, RawJob


def greenhouse_url(slug: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def greenhouse_job_url(slug: str, job_id: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"


def lever_url(slug: str) -> str:
    return f"https://api.lever.co/v0/postings/{slug}?mode=json"


def ashby_url(slug: str) -> str:
    return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"


def smartrecruiters_url(slug: str) -> str:
    return f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"


def workday_jobs_url(career_url: str, slug: str, site: str) -> str:
    parsed = urlparse(career_url or f"https://{slug}.wd1.myworkdayjobs.com/{site}")
    tenant = slug or parsed.netloc.split(".")[0]
    site_name = site or next((part for part in parsed.path.split("/") if part), "External")
    return f"{parsed.scheme}://{parsed.netloc}/wday/cxs/{tenant}/{site_name}/jobs"


def parse_json(result: FetchResult):
    if result.blocked:
        return None, f"blocked:{result.status}"
    if result.status >= 400 or not result.text:
        return None, f"http:{result.status}"
    try:
        return json.loads(result.text), "ok"
    except json.JSONDecodeError:
        return None, f"bad_json:{result.status}"


def _looks_relevant(job: RawJob, city: str) -> bool:
    return classify_role(job.title, job.description, job.location or city).keep


def _fill_greenhouse_descriptions(slug: str, jobs: list[RawJob], fetcher: PoliteFetcher) -> list[RawJob]:
    detailed: list[RawJob] = []
    for job in jobs:
        result = fetcher.get(greenhouse_job_url(slug, job.external_id))
        payload, status = parse_json(result)
        if status != "ok" or not isinstance(payload, dict):
            detailed.append(job)
            continue
        richer = parse_greenhouse_jobs({"jobs": [payload]}, job.company)
        detailed.append(richer[0] if richer else job)
    return detailed


def parse_smartrecruiters_jobs(payload: dict, company: str) -> list[RawJob]:
    jobs: list[RawJob] = []
    for item in payload.get("content") or payload.get("jobs") or []:
        location = ""
        loc = item.get("location") or {}
        if isinstance(loc, dict):
            location = ", ".join(
                part for part in (loc.get("city"), loc.get("region"), loc.get("country")) if part
            )
        jobs.append(
            RawJob(
                source="smartrecruiters",
                external_id=str(item.get("id") or item.get("uuid") or ""),
                title=item.get("name") or item.get("title") or "",
                company=company,
                location=location,
                url=item.get("ref") or item.get("applyUrl") or "",
                description=item.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text")
                or "",
            )
        )
    return jobs


def fetch_company_jobs(company: Company, fetcher: PoliteFetcher) -> tuple[list[RawJob], str]:
    kind = (company.ats_kind or "").lower()
    slug = company.ats_slug
    if kind == "greenhouse" and slug:
        result = fetcher.get(greenhouse_url(slug))
        payload, status = parse_json(result)
        if status != "ok":
            return [], status
        listed = parse_greenhouse_jobs(payload, company.name)
        relevant = [job for job in listed if _looks_relevant(job, company.city)]
        return _fill_greenhouse_descriptions(slug, relevant, fetcher), "ok"
    if kind == "lever" and slug:
        result = fetcher.get(lever_url(slug))
        payload, status = parse_json(result)
        if status != "ok":
            return [], status
        return parse_lever_jobs(payload, company.name), "ok"
    if kind == "ashby" and slug:
        result = fetcher.get(ashby_url(slug))
        payload, status = parse_json(result)
        if status != "ok":
            return [], status
        return parse_ashby_jobs(payload, company.name), "ok"
    if kind == "smartrecruiters" and slug:
        result = fetcher.get(smartrecruiters_url(slug))
        payload, status = parse_json(result)
        if status != "ok":
            return [], status
        return parse_smartrecruiters_jobs(payload, company.name), "ok"
    if kind == "workday" and (slug or company.career_url):
        url = workday_jobs_url(company.career_url, slug, company.ats_site)
        result = fetcher.post(url, {"appliedFacets": {}, "limit": 50, "offset": 0, "searchText": ""})
        payload, status = parse_json(result)
        if status != "ok":
            return [], status
        board = company.career_url or f"https://{slug}.wd1.myworkdayjobs.com/{company.ats_site or 'External'}"
        return parse_workday_jobs(payload, company.name, board), "ok"
    if company.career_url:
        result = fetcher.get(company.career_url)
        if result.blocked:
            return [], f"blocked:{result.status}"
        if result.status >= 400 or not result.text:
            return [], f"http:{result.status}"
        page_url = result.url or company.career_url
        jobs = parse_generic_listing(result.text, company, page_url)
        if jobs:
            return jobs, "ok"

        for link in listings_links_from_html(result.text, page_url)[:3]:
            nested = fetcher.get(link)
            if nested.blocked or nested.status >= 400 or not nested.text:
                continue
            hit_jobs = parse_generic_listing(nested.text, company, nested.url or link)
            if hit_jobs:
                return hit_jobs, "ok"
        return jobs, "ok"
    return [], "no_career_url"

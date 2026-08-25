import json

from jdscraper.crawl import fetch_company_jobs
from jdscraper.fetch.polite import FetchResult, PoliteFetcher, PolitePolicy
from jdscraper.models import Company

JOB = {
    "id": 7,
    "title": "SDET",
    "absolute_url": "https://boards.greenhouse.io/acme/jobs/7",
    "location": {"name": "Bengaluru"},
    "content": "<p>Playwright</p>",
}


def test_fetch_greenhouse_company_uses_public_board_api():
    seen: list[str] = []

    def transport(url: str) -> FetchResult:
        seen.append(url)
        if url.endswith("/jobs/7"):
            return FetchResult(url=url, status=200, text=json.dumps(JOB))
        return FetchResult(url=url, status=200, text=json.dumps({"jobs": [JOB]}))

    fetcher = PoliteFetcher(
        policy=PolitePolicy(min_delay_seconds=0, max_delay_seconds=0, same_host_min_seconds=0, honor_robots=False),
        transport=transport,
    )
    company = Company(name="Acme", ats_kind="greenhouse", ats_slug="acme", city="Bengaluru")
    jobs, status = fetch_company_jobs(company, fetcher)
    assert status == "ok"
    assert len(jobs) == 1
    assert jobs[0].title == "SDET"
    assert "Playwright" in jobs[0].description
    assert seen[0] == "https://boards-api.greenhouse.io/v1/boards/acme/jobs"
    assert seen[1] == "https://boards-api.greenhouse.io/v1/boards/acme/jobs/7"

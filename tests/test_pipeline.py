from pathlib import Path

from jdscraper.db import JobStore
from jdscraper.models import Company, RawJob
from jdscraper.pipeline import ingest_raw_jobs


def test_ingest_keeps_only_bangalore_qa(tmp_path: Path):
    store = JobStore(tmp_path / "t.sqlite")
    company = store.upsert_company(Company(name="Acme", domain="saas", city="Bengaluru"))
    kept = ingest_raw_jobs(
        store,
        company,
        [
            RawJob(
                source="greenhouse",
                external_id="1",
                title="Senior SDET",
                company="Acme",
                location="Bengaluru",
                url="https://example.com/1",
                description="8-12 years. Playwright and TypeScript.",
            ),
            RawJob(
                source="greenhouse",
                external_id="2",
                title="Backend Engineer",
                company="Acme",
                location="Bengaluru",
                url="https://example.com/2",
                description="Go microservices.",
            ),
            RawJob(
                source="greenhouse",
                external_id="3",
                title="SDET",
                company="Acme",
                location="Pune",
                url="https://example.com/3",
                description="Selenium.",
            ),
        ],
    )
    assert len(kept) == 1
    jobs = store.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].role == "Senior SDET"
    assert jobs[0].years_min == 8
    assert jobs[0].years_max == 12
    assert "Playwright" in jobs[0].tech_stack
    assert jobs[0].domain == "saas"
    assert jobs[0].company_name == "Acme"

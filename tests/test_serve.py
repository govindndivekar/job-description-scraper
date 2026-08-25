from pathlib import Path

from jdscraper.db import JobStore
from jdscraper.models import Company, JobPosting
from jdscraper.serve import dispatch, parse_query


def test_dispatch_lists_jobs_and_unknown_analysis(tmp_path: Path):
    store = JobStore(tmp_path / "t.sqlite")
    company = store.upsert_company(Company(name="Acme", domain="saas", ats_kind="greenhouse"))
    store.save_job(
        JobPosting(
            company_id=company.id,
            company_name="Acme",
            role="SDET",
            description="Playwright",
            tech_stack=["Playwright"],
            domain="saas",
            url="https://e/1",
            source="greenhouse",
            external_id="1",
        )
    )
    jobs = dispatch(store, "/api/jobs", parse_query("q=sdet"))
    assert jobs.status == 200
    assert jobs.body[0]["role"] == "SDET"
    missing = dispatch(store, "/api/analysis/nope", {})
    assert missing.status == 404
    listed = dispatch(store, "/api/analysis", {})
    assert any(item["name"] == "stack-demand" for item in listed.body)

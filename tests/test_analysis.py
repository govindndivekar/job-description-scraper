from pathlib import Path

from jdscraper.analysis import get_analysis, list_analyses, run_analysis
from jdscraper.db import JobStore
from jdscraper.models import Company, JobPosting


def test_builtin_analyses_are_registered():
    names = {item["name"] for item in list_analyses()}
    assert "stack-demand" in names
    assert "experience-bands" in names
    assert "domain-coverage" in names


def test_stack_demand_ranks_tools(tmp_path: Path):
    store = JobStore(tmp_path / "t.sqlite")
    company = store.upsert_company(Company(name="Acme", domain="saas"))
    store.save_job(
        JobPosting(
            company_id=company.id,
            company_name="Acme",
            role="SDET",
            description="a",
            tech_stack=["Playwright", "Java"],
            domain="saas",
            url="https://e/1",
            source="greenhouse",
            external_id="1",
        )
    )
    store.save_job(
        JobPosting(
            company_id=company.id,
            company_name="Acme",
            role="QA",
            description="b",
            tech_stack=["Playwright"],
            domain="saas",
            url="https://e/2",
            source="greenhouse",
            external_id="2",
        )
    )
    result = run_analysis("stack-demand", store)
    assert result["name"] == "stack-demand"
    assert result["rows"][0]["label"] == "Playwright"
    assert result["rows"][0]["value"] == 2
    assert get_analysis("missing") is None

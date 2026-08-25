from pathlib import Path

from jdscraper.db import JobStore
from jdscraper.models import Company, JobPosting


def test_upsert_company_is_idempotent_by_name(tmp_path: Path):
    store = JobStore(tmp_path / "t.sqlite")
    first = store.upsert_company(
        Company(name="Bosch", website="https://www.bosch.in", domain="automotive", city="Bengaluru")
    )
    second = store.upsert_company(
        Company(
            name="Bosch",
            website="https://www.bosch.com",
            domain="automotive",
            city="Bengaluru",
            career_url="https://www.bosch.in/careers",
        )
    )
    assert first.id == second.id
    loaded = store.get_company("Bosch")
    assert loaded is not None
    assert loaded.career_url == "https://www.bosch.in/careers"
    assert loaded.website == "https://www.bosch.com"
    assert store.company_count() == 1


def test_save_job_stores_required_columns(tmp_path: Path):
    store = JobStore(tmp_path / "t.sqlite")
    company = store.upsert_company(Company(name="Atlassian", domain="saas", city="Bengaluru"))
    job = store.save_job(
        JobPosting(
            company_id=company.id,
            company_name="Atlassian",
            role="Senior SDET",
            years_min=8,
            years_max=12,
            description="Playwright and TypeScript.",
            tech_stack=["Playwright", "TypeScript"],
            domain="saas",
            location="Bengaluru",
            url="https://www.atlassian.com/company/careers/details/123",
            source="greenhouse",
            external_id="123",
        )
    )
    rows = store.list_jobs()
    assert len(rows) == 1
    saved = rows[0]
    assert saved.id == job.id
    assert saved.role == "Senior SDET"
    assert saved.company_name == "Atlassian"
    assert saved.years_min == 8
    assert saved.description.startswith("Playwright")
    assert saved.tech_stack == ["Playwright", "TypeScript"]
    assert saved.domain == "saas"


def test_duplicate_external_id_updates_same_row(tmp_path: Path):
    store = JobStore(tmp_path / "t.sqlite")
    company = store.upsert_company(Company(name="Stripe", domain="fintech", city="Bengaluru"))
    store.save_job(
        JobPosting(
            company_id=company.id,
            company_name="Stripe",
            role="SDET",
            description="old",
            url="https://example.com/1",
            source="greenhouse",
            external_id="42",
        )
    )
    store.save_job(
        JobPosting(
            company_id=company.id,
            company_name="Stripe",
            role="Staff SDET",
            description="new",
            url="https://example.com/1",
            source="greenhouse",
            external_id="42",
        )
    )
    jobs = store.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].role == "Staff SDET"
    assert jobs[0].description == "new"


def test_due_companies_skips_recently_crawled(tmp_path: Path):
    store = JobStore(tmp_path / "t.sqlite")
    a = store.upsert_company(Company(name="A", career_url="https://a.example/jobs", city="Bengaluru"))
    b = store.upsert_company(Company(name="B", career_url="https://b.example/jobs", city="Bengaluru"))
    store.mark_crawled(a.id, status="ok")
    due = store.due_companies(recrawl_days=7)
    names = {c.name for c in due}
    assert "B" in names
    assert "A" not in names

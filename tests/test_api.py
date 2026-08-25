from pathlib import Path

from jdscraper.api import catalog_stats, job_to_dict
from jdscraper.db import JobStore
from jdscraper.models import Company, JobPosting


def _seeded(tmp_path: Path) -> JobStore:
    store = JobStore(tmp_path / "t.sqlite")
    acme = store.upsert_company(
        Company(name="Acme", domain="saas", city="Bengaluru", ats_kind="greenhouse", career_url="https://a.example/jobs")
    )
    bosch = store.upsert_company(Company(name="Bosch", domain="automotive", city="Bengaluru", source="wikipedia"))
    store.save_job(
        JobPosting(
            company_id=acme.id,
            company_name="Acme",
            role="Senior SDET",
            years_min=8,
            years_max=12,
            description="Playwright and TypeScript.",
            tech_stack=["Playwright", "TypeScript"],
            domain="saas",
            location="Bengaluru",
            url="https://example.com/1",
            source="greenhouse",
            external_id="1",
        )
    )
    store.mark_crawled(acme.id, "ok")
    assert bosch.id is not None
    return store


def test_job_to_dict_exposes_viewer_fields(tmp_path: Path):
    store = _seeded(tmp_path)
    payload = job_to_dict(store.list_jobs()[0])
    assert payload["role"] == "Senior SDET"
    assert payload["company"] == "Acme"
    assert payload["tech_stack"] == ["Playwright", "TypeScript"]
    assert payload["years_min"] == 8
    assert payload["url"].startswith("https://")


def test_catalog_stats_counts_coverage(tmp_path: Path):
    stats = catalog_stats(_seeded(tmp_path))
    assert stats["companies"] == 2
    assert stats["jobs"] == 1
    assert stats["with_career"] == 1
    assert stats["with_ats"] == 1
    assert stats["crawled"] == 1
    domains = {row["name"]: row for row in stats["domains"]}
    assert domains["saas"]["jobs"] == 1
    assert domains["automotive"]["companies"] == 1
    tech = {row["name"]: row["count"] for row in stats["tech"]}
    assert tech["Playwright"] == 1

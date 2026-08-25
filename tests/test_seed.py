from pathlib import Path

from jdscraper.discover.seed import load_seed
from jdscraper.models import Company


def test_load_seed_reads_name_website_and_domain(tmp_path: Path):
    path = tmp_path / "seed.yaml"
    path.write_text(
        """
companies:
  - name: Bosch
    website: https://www.bosch.in
    domain: automotive
    city: Bengaluru
  - name: Atlassian
    website: https://www.atlassian.com
    career_url: https://www.atlassian.com/company/careers
    ats_kind: greenhouse
    ats_slug: atlassian
    domain: saas
""",
        encoding="utf-8",
    )
    companies = load_seed(path)
    assert [c.name for c in companies] == ["Bosch", "Atlassian"]
    assert all(isinstance(c, Company) for c in companies)
    assert companies[1].ats_kind == "greenhouse"
    assert companies[1].ats_slug == "atlassian"
    assert companies[0].domain == "automotive"

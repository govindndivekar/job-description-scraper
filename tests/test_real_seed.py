from pathlib import Path

from jdscraper.config import ROOT
from jdscraper.discover.seed import load_seed


def test_bundled_seed_has_unique_names_and_ats_rows():
    companies = load_seed(ROOT / "config" / "companies.seed.yaml")
    names = [c.name for c in companies]
    assert len(names) >= 80
    assert len(names) == len(set(name.lower() for name in names))
    ats = [c for c in companies if c.ats_kind]
    assert any(c.ats_kind == "greenhouse" for c in ats)
    assert any(c.domain == "semiconductor" for c in companies)
    assert any(c.domain == "aerospace" for c in companies)
    assert all(c.city == "Bengaluru" for c in companies)

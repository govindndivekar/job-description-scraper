import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "enrich_naukri_seed", ROOT / "scripts" / "enrich_naukri_seed.py"
)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_rejects_air_inc_for_air_india():
    assert mod.score_candidate("Air India", "Air", "air.inc") < 0.68
    assert mod.score_candidate("Air India", "Air India", "airindia.com") >= 0.68


def test_prefers_indian_data_patterns():
    uk = mod.score_candidate("Data Patterns", "Data Patterns", "datapatterns.co.uk")
    india = mod.score_candidate("Data Patterns", "Data Patterns", "datapatternsindia.com")
    assert india > uk
    assert india >= 0.68


def test_cae_and_unrelated_short_domain():
    assert mod.domain_related("CAE", "cae.com")
    assert not mod.domain_related("Air India", "air.inc")


def test_rejects_wrong_short_and_extra_name_hits():
    assert mod.score_candidate("ZF", "ZF.ro", "zf.ro") < 0.68
    assert mod.score_candidate("ZF", "ZF", "zf.com") >= 0.68
    assert mod.score_candidate("Garrett", "Garrett Wade", "garrettwade.com") < 0.68
    assert mod.score_candidate("M360 Research", "4M Research", "4mresearch.com") < 0.68
    assert mod.score_candidate("ANTOLIN", "AntoLin Cellars", "antolincellars.com") < 0.68


def test_patch_yaml_inserts_urls_and_drops_junk():
    text = """companies:
  - name: Atlassian
    website: https://www.atlassian.com
    career_url: https://www.atlassian.com/company/careers
    domain: saas
  # --- Naukri: aerospace (2) ---
  - name: Aequs
    domain: aerospace
    source: naukri
  - name: Naukri
    domain: unknown
    source: naukri
  - name: Alpha Design Technologies
    domain: aerospace
    source: naukri
"""
    updates = {
        "Aequs": {"website": "https://www.aequs.com", "career_url": "https://www.aequs.com/careers"},
        "Alpha Design Technologies": {
            "website": mod.MANUAL_URLS["Alpha Design Technologies"][0],
            "career_url": mod.MANUAL_URLS["Alpha Design Technologies"][1],
        },
    }
    out = mod.patch_yaml(text, updates)
    assert "name: Naukri\n" not in out
    assert "website: https://www.aequs.com" in out
    assert "career_url: https://www.adtl.co.in/careers" in out
    assert "Atlassian" in out
    assert "Naukri" in mod.drop_names()

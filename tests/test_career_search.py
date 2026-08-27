from jdscraper.careers.search import pick_career_hits, search_query


def test_search_query_names_company_and_jobs():
    q = search_query("Acme", "https://www.acme.com")
    assert "Acme" in q
    assert "careers" in q.lower() or "jobs" in q.lower()


def test_pick_career_hits_keeps_same_host_and_ats():
    hits = [
        "https://www.linkedin.com/company/acme/jobs",
        "https://www.acme.com/about",
        "https://www.acme.com/careers/openings",
        "https://job-boards.greenhouse.io/acme",
        "https://naukri.com/acme-jobs",
    ]
    picked = pick_career_hits("Acme", "https://www.acme.com", hits)
    assert "https://www.acme.com/careers/openings" in picked
    assert "https://job-boards.greenhouse.io/acme" in picked
    assert all("linkedin.com" not in url for url in picked)
    assert all("naukri.com" not in url for url in picked)

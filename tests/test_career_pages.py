from jdscraper.careers.pages import listings_links_from_html, page_kind


def test_marketing_career_page_is_not_a_listing():
    html = """
    <html><body>
      <h1>Life at Acme</h1>
      <p>Benefits, culture, and our Bangalore office.</p>
      <a href="/careers/openings">View current openings</a>
    </body></html>
    """
    assert page_kind(html, "https://www.acme.com/careers") == "marketing"
    links = listings_links_from_html(html, "https://www.acme.com/careers")
    assert "https://www.acme.com/careers/openings" in links


def test_job_listing_page_has_roles():
    html = """
    <html><body>
      <h1>Open positions</h1>
      <a href="/jobs/123">Senior SDET</a>
      <a href="/jobs/124">QA Automation Engineer</a>
    </body></html>
    """
    assert page_kind(html, "https://www.acme.com/careers/jobs") == "listings"


def test_greenhouse_embed_counts_as_listings():
    html = '<script src="https://boards.greenhouse.io/embed/job_board/js?for=acme"></script>'
    assert page_kind(html, "https://www.acme.com/careers") == "listings"

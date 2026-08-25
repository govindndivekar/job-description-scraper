from jdscraper.careers.resolve import career_links_from_html, guess_career_urls


def test_career_links_prefer_careers_and_jobs_hrefs():
    html = """
    <html>
      <a href="/about">About</a>
      <a href="https://www.acme.com/careers">Careers</a>
      <a href="/jobs/india">India jobs</a>
      <a href="https://jobs.lever.co/acme">Open roles</a>
    </html>
    """
    links = career_links_from_html(html, base_url="https://www.acme.com/")
    assert "https://www.acme.com/careers" in links
    assert "https://www.acme.com/jobs/india" in links
    assert "https://jobs.lever.co/acme" in links
    assert all("about" not in link for link in links)


def test_guess_career_urls_covers_common_paths():
    urls = guess_career_urls("https://www.bosch.in")
    assert "https://www.bosch.in/careers" in urls
    assert "https://www.bosch.in/jobs" in urls
    assert urls[0].startswith("https://")

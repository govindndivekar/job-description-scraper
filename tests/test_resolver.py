from jdscraper.careers.resolver import resolve_company
from jdscraper.fetch.polite import FetchResult
from jdscraper.models import Company


class FakeFetcher:
    def __init__(self, pages: dict[str, FetchResult]) -> None:
        self.pages = pages

    def get(self, url: str) -> FetchResult:
        return self.pages.get(url, FetchResult(url=url, status=404, text="", blocked=False))


def test_dead_career_url_is_cleared():
    company = Company(name="Acme", website="https://www.acme.com", career_url="https://www.acme.com/careers")
    fetcher = FakeFetcher({})
    updated = resolve_company(company, fetcher)
    assert updated.career_url == ""


def test_marketing_page_follows_current_openings():
    company = Company(name="Acme", website="https://www.acme.com", career_url="https://www.acme.com/careers")
    fetcher = FakeFetcher(
        {
            "https://www.acme.com/careers": FetchResult(
                url="https://www.acme.com/careers",
                status=200,
                text='<a href="/careers/openings">View current openings</a>',
            ),
            "https://www.acme.com/careers/openings": FetchResult(
                url="https://www.acme.com/careers/openings",
                status=200,
                text='<a href="/jobs/1">Senior SDET</a><a href="/jobs/2">QA Automation Engineer</a>',
            ),
        }
    )
    updated = resolve_company(company, fetcher)
    assert updated.career_url == "https://www.acme.com/careers/openings"


def test_search_hits_can_supply_ats_board():
    company = Company(name="Acme", website="https://www.acme.com")
    fetcher = FakeFetcher(
        {"https://www.acme.com": FetchResult(url="https://www.acme.com", status=200, text="<h1>Hello</h1>")}
    )

    def search(_company: Company) -> list[str]:
        return ["https://job-boards.greenhouse.io/acme"]

    updated = resolve_company(company, fetcher, search=search)
    assert updated.ats_kind == "greenhouse"
    assert updated.ats_slug == "acme"

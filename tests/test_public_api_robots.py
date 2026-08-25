from jdscraper.fetch.polite import FetchResult, PoliteFetcher, PolitePolicy


def test_public_wikipedia_api_is_not_blocked_by_site_robots():
    clock_calls = {"robots": 0}

    def transport(url: str) -> FetchResult:
        if url.endswith("/robots.txt"):
            clock_calls["robots"] += 1
            return FetchResult(
                url=url,
                status=200,
                text="User-agent: *\nDisallow: /w/\n",
            )
        return FetchResult(url=url, status=200, text='{"query":{"categorymembers":[]}}')

    fetcher = PoliteFetcher(
        policy=PolitePolicy(min_delay_seconds=0, max_delay_seconds=0, honor_robots=True),
        transport=transport,
    )
    result = fetcher.get(
        "https://en.wikipedia.org/w/api.php?action=query&list=categorymembers"
    )
    assert result.blocked is False
    assert result.status == 200
    assert clock_calls["robots"] == 0

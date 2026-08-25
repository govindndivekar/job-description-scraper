from jdscraper.fetch.polite import PoliteFetcher, PolitePolicy, FetchResult


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_same_host_waits_for_cooldown():
    clock = FakeClock()
    policy = PolitePolicy(
        min_delay_seconds=10,
        max_delay_seconds=10,
        same_host_min_seconds=60,
        honor_robots=False,
    )
    calls: list[str] = []

    def transport(url: str) -> FetchResult:
        calls.append(url)
        return FetchResult(url=url, status=200, text="ok", blocked=False)

    fetcher = PoliteFetcher(policy=policy, transport=transport, clock=clock)
    fetcher.get("https://jobs.lever.co/acme")
    fetcher.get("https://jobs.lever.co/beta")
    assert calls == ["https://jobs.lever.co/acme", "https://jobs.lever.co/beta"]
    assert clock.sleeps
    assert max(clock.sleeps) >= 60


def test_stop_on_forbidden_marks_blocked_and_skips_host():
    clock = FakeClock()
    policy = PolitePolicy(min_delay_seconds=0, max_delay_seconds=0, same_host_min_seconds=0, honor_robots=False)
    hits = {"n": 0}

    def transport(url: str) -> FetchResult:
        hits["n"] += 1
        return FetchResult(url=url, status=403, text="no", blocked=True)

    fetcher = PoliteFetcher(policy=policy, transport=transport, clock=clock)
    first = fetcher.get("https://careers.example.com/jobs")
    second = fetcher.get("https://careers.example.com/jobs/2")
    assert first.blocked is True
    assert second.blocked is True
    assert second.status == 403
    assert hits["n"] == 1


def test_robots_disallow_does_not_fetch():
    clock = FakeClock()
    policy = PolitePolicy(min_delay_seconds=0, max_delay_seconds=0, honor_robots=True)

    def transport(url: str) -> FetchResult:
        if url.endswith("/robots.txt"):
            return FetchResult(url=url, status=200, text="User-agent: *\nDisallow: /hidden\n", blocked=False)
        raise AssertionError(f"should not fetch {url}")

    fetcher = PoliteFetcher(policy=policy, transport=transport, clock=clock)
    result = fetcher.get("https://example.com/hidden/jobs")
    assert result.blocked is True
    assert result.status == 0
    assert "robots" in (result.detail or "")

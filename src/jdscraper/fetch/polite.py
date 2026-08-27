from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

DEFAULT_STOP = (401, 403, 429, 503)
PUBLIC_API_PREFIXES = (
    "https://en.wikipedia.org/w/api.php",
    "https://www.wikidata.org/w/api.php",
    "https://boards-api.greenhouse.io/",
    "https://api.lever.co/",
    "https://api.ashbyhq.com/",
    "https://api.smartrecruiters.com/",
    "https://www.googleapis.com/customsearch/",
)


@dataclass(frozen=True, slots=True)
class PolitePolicy:
    min_delay_seconds: float = 15
    max_delay_seconds: float = 45
    same_host_min_seconds: float = 60
    honor_robots: bool = True
    timeout_seconds: float = 25
    stop_on_status: tuple[int, ...] = DEFAULT_STOP
    user_agent: str = "JDScraper/0.1 (+personal job search; govind_divekar@yahoo.com)"


@dataclass(slots=True)
class FetchResult:
    url: str
    status: int
    text: str = ""
    blocked: bool = False
    detail: str = ""


class RealClock:
    def time(self) -> float:
        import time

        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        import time

        if seconds > 0:
            time.sleep(seconds)


class PoliteFetcher:
    def __init__(self, policy: PolitePolicy, transport, clock=None, rng=None, post_transport=None):
        self.policy = policy
        self.transport = transport
        self.post_transport = post_transport
        self.clock = clock or RealClock()
        self.rng = rng
        self._last_host: dict[str, float] = {}
        self._last_any: float | None = None
        self._blocked_hosts: set[str] = set()
        self._robots: dict[str, RobotFileParser | None] = {}

    def _host(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    def _delay_before(self, url: str) -> None:
        now = self.clock.time()
        wait = 0.0
        if self._last_any is not None:
            lo = self.policy.min_delay_seconds
            hi = max(lo, self.policy.max_delay_seconds)
            gap = hi if hi == lo else (self.rng.uniform(lo, hi) if self.rng else lo)
            wait = max(wait, gap - (now - self._last_any))
        host = self._host(url)
        last = self._last_host.get(host)
        if last is not None:
            wait = max(wait, self.policy.same_host_min_seconds - (now - last))
        if wait > 0:
            self.clock.sleep(wait)

    def _mark(self, url: str) -> None:
        now = self.clock.time()
        self._last_any = now
        self._last_host[self._host(url)] = now

    def _allowed_by_robots(self, url: str) -> tuple[bool, str]:
        if not self.policy.honor_robots:
            return True, ""
        if any(url.startswith(prefix) for prefix in PUBLIC_API_PREFIXES):
            return True, ""
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            robots_url = origin + "/robots.txt"
            try:
                result = self.transport(robots_url)
            except Exception as exc:  # noqa: BLE001 - transport failures mean "allow"
                self._robots[origin] = None
                return True, str(exc)
            parser = RobotFileParser()
            parser.set_url(robots_url)
            if result.status >= 400:
                self._robots[origin] = None
            else:
                parser.parse((result.text or "").splitlines())
                self._robots[origin] = parser
        parser = self._robots[origin]
        if parser is None:
            return True, ""
        if parser.can_fetch(self.policy.user_agent, url):
            return True, ""
        return False, "robots.txt disallows this path"

    def get(self, url: str) -> FetchResult:
        host = self._host(url)
        if host in self._blocked_hosts:
            return FetchResult(url=url, status=403, blocked=True, detail="host previously blocked")
        allowed, reason = self._allowed_by_robots(url)
        if not allowed:
            return FetchResult(url=url, status=0, blocked=True, detail=reason)
        self._delay_before(url)
        result = self.transport(url)
        self._mark(url)
        if result.status in self.policy.stop_on_status:
            self._blocked_hosts.add(host)
            result.blocked = True
        return result

    def post(self, url: str, json_body: dict | None = None) -> FetchResult:
        host = self._host(url)
        if host in self._blocked_hosts:
            return FetchResult(url=url, status=403, blocked=True, detail="host previously blocked")
        sender = self.post_transport
        if sender is None:
            return FetchResult(url=url, status=0, blocked=True, detail="POST not configured")
        self._delay_before(url)
        result = sender(url, json_body)
        self._mark(url)
        if result.status in self.policy.stop_on_status:
            self._blocked_hosts.add(host)
            result.blocked = True
        return result

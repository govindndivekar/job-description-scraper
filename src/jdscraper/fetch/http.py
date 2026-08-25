from __future__ import annotations

import httpx

from jdscraper.fetch.polite import FetchResult, PolitePolicy


class HttpxTransport:
    def __init__(self, policy: PolitePolicy):
        self.policy = policy
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            "Accept-Language": "en-IN,en;q=0.9",
        }

    def get(self, url: str) -> FetchResult:
        return self._request("GET", url)

    def post(self, url: str, json_body: dict | None = None) -> FetchResult:
        return self._request("POST", url, json_body)

    def __call__(self, url: str) -> FetchResult:
        return self.get(url)

    def _request(self, method: str, url: str, json_body: dict | None = None) -> FetchResult:
        headers = dict(self.headers)
        if "wikipedia.org" in url or "wikidata.org" in url:
            headers["User-Agent"] = self.policy.user_agent
            headers["Accept"] = "application/json"
        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                json=json_body,
                timeout=self.policy.timeout_seconds,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            return FetchResult(url=url, status=0, blocked=False, detail=str(exc))
        return FetchResult(url=str(response.url), status=response.status_code, text=response.text)

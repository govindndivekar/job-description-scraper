from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from jdscraper.analysis import get_analysis, list_analyses, run_analysis
from jdscraper.api import catalog_stats, company_to_dict, filter_companies, filter_jobs, job_to_dict
from jdscraper.config import ROOT
from jdscraper.db import JobStore


@dataclass(slots=True)
class ApiResponse:
    status: int
    body: dict | list
    content_type: str = "application/json; charset=utf-8"


def _q(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return values[0].strip() if values else ""


def dispatch(store: JobStore, path: str, query: dict[str, list[str]]) -> ApiResponse:
    if path == "/api/jobs":
        jobs = filter_jobs(
            store.list_jobs(),
            query=_q(query, "q"),
            domain=_q(query, "domain"),
            company=_q(query, "company"),
        )
        return ApiResponse(200, [job_to_dict(job) for job in jobs])
    if path == "/api/companies":
        companies = filter_companies(
            store.list_companies(),
            query=_q(query, "q"),
            domain=_q(query, "domain"),
            source=_q(query, "source"),
            ats=_q(query, "ats"),
        )
        return ApiResponse(200, [company_to_dict(company) for company in companies])
    if path == "/api/stats":
        return ApiResponse(200, catalog_stats(store))
    if path == "/api/analysis":
        return ApiResponse(200, list_analyses())
    if path.startswith("/api/analysis/"):
        name = path.removeprefix("/api/analysis/").strip("/")
        if not get_analysis(name):
            return ApiResponse(404, {"error": f"unknown analysis: {name}"})
        return ApiResponse(200, run_analysis(name, store))
    return ApiResponse(404, {"error": "not found"})


def encode(response: ApiResponse) -> bytes:
    return json.dumps(response.body, ensure_ascii=False).encode("utf-8")


def parse_query(raw: str) -> dict[str, list[str]]:
    return parse_qs(raw or "", keep_blank_values=False)


class ViewerHandler(SimpleHTTPRequestHandler):
    db_path: Path
    web_dir: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.web_dir), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            store = JobStore(self.db_path)
            try:
                response = dispatch(store, parsed.path, parse_qs(parsed.query))
            finally:
                store.close()
            payload = encode(response)
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
        if parsed.path in {"", "/"}:
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)


def run_server(host: str, port: int, db_path: Path, web_dir: Path | None = None) -> ThreadingHTTPServer:
    resolved_db = Path(db_path)
    resolved_web = web_dir or (ROOT / "web")

    class BoundHandler(ViewerHandler):
        db_path = resolved_db
        web_dir = resolved_web

    return ThreadingHTTPServer((host, port), BoundHandler)

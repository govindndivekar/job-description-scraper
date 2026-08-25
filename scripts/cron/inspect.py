#!/usr/bin/env python3
"""Report new QA jobs and coverage movement. Silent when nothing changed."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DB, STATE  # noqa: E402


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"job_keys": [], "crawled": 0, "jobs": 0, "with_career": 0}


def catalog() -> dict:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    companies = conn.execute("SELECT * FROM companies").fetchall()
    jobs = conn.execute(
        "SELECT role, company_name, years_min, years_max, domain, url "
        "FROM jobs ORDER BY fetched_at DESC, id DESC"
    ).fetchall()
    conn.close()
    job_rows = []
    for job in jobs:
        years = f"{job['years_min']}+" if job["years_min"] is not None else "?"
        job_rows.append(
            {
                "key": job["url"] or f"{job['company_name']}|{job['role']}",
                "line": (
                    f"{job['role']} | {job['company_name']} | {years} yrs | "
                    f"{job['domain'] or '-'} | {job['url']}"
                ),
            }
        )
    return {
        "companies": len(companies),
        "with_career": sum(1 for row in companies if row["career_url"]),
        "crawled": sum(1 for row in companies if row["last_crawled_at"]),
        "jobs": len(jobs),
        "job_rows": job_rows,
    }


def main() -> int:
    if not DB.exists():
        return 0
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = load_state()
    now = catalog()
    seen = set(state.get("job_keys") or [])
    new_jobs = [row for row in now["job_rows"] if row["key"] not in seen]
    coverage_moved = (
        now["crawled"] != state.get("crawled")
        or now["jobs"] != state.get("jobs")
        or now["with_career"] != state.get("with_career")
    )
    STATE.write_text(
        json.dumps(
            {
                "job_keys": [row["key"] for row in now["job_rows"]],
                "crawled": now["crawled"],
                "jobs": now["jobs"],
                "with_career": now["with_career"],
            },
            indent=2,
        )
    )
    if not new_jobs and not coverage_moved:
        return 0
    print("JDScraper inspect")
    print(
        f"jobs={now['jobs']} crawled={now['crawled']}/{now['companies']} "
        f"with_career={now['with_career']}"
    )
    if new_jobs:
        print(f"new QA jobs: {len(new_jobs)}")
        for row in new_jobs:
            print(row["line"])
    else:
        print("No new QA jobs this tick.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

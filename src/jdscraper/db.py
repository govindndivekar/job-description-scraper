from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jdscraper.models import Company, JobPosting

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    website TEXT NOT NULL DEFAULT '',
    career_url TEXT NOT NULL DEFAULT '',
    domain TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT 'Bengaluru',
    ats_kind TEXT NOT NULL DEFAULT '',
    ats_slug TEXT NOT NULL DEFAULT '',
    ats_site TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'seed',
    last_crawled_at TEXT,
    last_status TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    role TEXT NOT NULL,
    years_min INTEGER,
    years_max INTEGER,
    description TEXT NOT NULL,
    tech_stack TEXT NOT NULL DEFAULT '[]',
    domain TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE (company_id, source, external_id),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_company(row: sqlite3.Row) -> Company:
    return Company(
        id=row["id"],
        name=row["name"],
        website=row["website"],
        career_url=row["career_url"],
        domain=row["domain"],
        city=row["city"],
        ats_kind=row["ats_kind"],
        ats_slug=row["ats_slug"],
        ats_site=row["ats_site"],
        source=row["source"],
        last_crawled_at=row["last_crawled_at"],
        last_status=row["last_status"],
    )


def _row_job(row: sqlite3.Row) -> JobPosting:
    return JobPosting(
        id=row["id"],
        company_id=row["company_id"],
        company_name=row["company_name"],
        role=row["role"],
        years_min=row["years_min"],
        years_max=row["years_max"],
        description=row["description"],
        tech_stack=json.loads(row["tech_stack"] or "[]"),
        domain=row["domain"],
        location=row["location"],
        url=row["url"],
        source=row["source"],
        external_id=row["external_id"],
        fetched_at=row["fetched_at"],
    )


class JobStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def upsert_company(self, company: Company) -> Company:
        now = _now()
        existing = self.get_company(company.name)
        if existing is None:
            cur = self._conn.execute(
                """
                INSERT INTO companies (
                    name, website, career_url, domain, city,
                    ats_kind, ats_slug, ats_site, source, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company.name,
                    company.website,
                    company.career_url,
                    company.domain,
                    company.city,
                    company.ats_kind,
                    company.ats_slug,
                    company.ats_site,
                    company.source,
                    now,
                    now,
                ),
            )
            self._conn.commit()
            company.id = cur.lastrowid
            return company

        website = company.website or existing.website
        career_url = company.career_url or existing.career_url
        domain = company.domain or existing.domain
        city = company.city or existing.city
        ats_kind = company.ats_kind or existing.ats_kind
        ats_slug = company.ats_slug or existing.ats_slug
        ats_site = company.ats_site or existing.ats_site
        source = company.source or existing.source
        self._conn.execute(
            """
            UPDATE companies
            SET website=?, career_url=?, domain=?, city=?,
                ats_kind=?, ats_slug=?, ats_site=?, source=?, updated_at=?
            WHERE id=?
            """,
            (
                website,
                career_url,
                domain,
                city,
                ats_kind,
                ats_slug,
                ats_site,
                source,
                now,
                existing.id,
            ),
        )
        self._conn.commit()
        existing.website = website
        existing.career_url = career_url
        existing.domain = domain
        existing.city = city
        existing.ats_kind = ats_kind
        existing.ats_slug = ats_slug
        existing.ats_site = ats_site
        existing.source = source
        return existing

    def get_company(self, name: str) -> Company | None:
        row = self._conn.execute(
            "SELECT * FROM companies WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
        return _row_company(row) if row else None

    def company_count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0])

    def list_companies(self) -> list[Company]:
        rows = self._conn.execute("SELECT * FROM companies ORDER BY name COLLATE NOCASE").fetchall()
        return [_row_company(row) for row in rows]

    def save_job(self, job: JobPosting) -> JobPosting:
        now = _now()
        self._conn.execute(
            """
            INSERT INTO jobs (
                company_id, company_name, role, years_min, years_max,
                description, tech_stack, domain, location, url,
                source, external_id, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id, source, external_id) DO UPDATE SET
                company_name=excluded.company_name,
                role=excluded.role,
                years_min=excluded.years_min,
                years_max=excluded.years_max,
                description=excluded.description,
                tech_stack=excluded.tech_stack,
                domain=excluded.domain,
                location=excluded.location,
                url=excluded.url,
                fetched_at=excluded.fetched_at
            """,
            (
                job.company_id,
                job.company_name,
                job.role,
                job.years_min,
                job.years_max,
                job.description,
                json.dumps(job.tech_stack, ensure_ascii=False),
                job.domain,
                job.location,
                job.url,
                job.source,
                job.external_id,
                now,
            ),
        )
        self._conn.commit()
        row = self._conn.execute(
            """
            SELECT * FROM jobs
            WHERE company_id=? AND source=? AND external_id=?
            """,
            (job.company_id, job.source, job.external_id),
        ).fetchone()
        return _row_job(row)

    def list_jobs(self) -> list[JobPosting]:
        rows = self._conn.execute("SELECT * FROM jobs ORDER BY fetched_at DESC, id DESC").fetchall()
        return [_row_job(row) for row in rows]

    def mark_crawled(self, company_id: int, status: str) -> None:
        self._conn.execute(
            "UPDATE companies SET last_crawled_at=?, last_status=?, updated_at=? WHERE id=?",
            (_now(), status, _now(), company_id),
        )
        self._conn.commit()

    def due_companies(self, recrawl_days: int = 7, require_career: bool = True) -> list[Company]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=recrawl_days)).isoformat()
        sql = """
            SELECT * FROM companies
            WHERE (last_crawled_at IS NULL OR last_crawled_at < ?)
        """
        params: list[object] = [cutoff]
        if require_career:
            sql += " AND career_url != ''"
        sql += " ORDER BY last_crawled_at IS NOT NULL, name COLLATE NOCASE"
        return [_row_company(row) for row in self._conn.execute(sql, params).fetchall()]

    def unresolved_companies(self) -> list[Company]:
        rows = self._conn.execute(
            "SELECT * FROM companies WHERE career_url = '' OR ats_kind = '' ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [_row_company(row) for row in rows]

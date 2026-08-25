# Bangalore QA Career-Page Scraper Implementation Plan

> **For Hermes:** Implement staged, polite career-page collection. Do not burst-crawl.

**Goal:** Discover Bangalore employers (software plus semiconductor, manufacturing, aerospace, and other domains with software roles), resolve public career pages, fetch QA / SDET / test-automation listings without looking like a bot, and store structured JDs in a local SQLite database.

**Architecture:** Seven isolated stages so request patterns stay human: catalog companies → resolve career/ATS URLs → fetch one company at a time with jittered delays → filter QA locally → extract fields locally → upsert SQLite. Prefer official public ATS JSON APIs (Greenhouse, Lever, Ashby, SmartRecruiters, Workday CXS) over HTML crawling. Never log in or bypass challenges.

**Tech Stack:** Python 3.11, uv, httpx, beautifulsoup4, pyyaml, sqlite3, pytest.

---

## Constraints

- Location: Bengaluru / Bangalore only (WFO or hybrid). Drop other-city and fully-remote-elsewhere posts.
- Roles: QA, software testing, test automation, SDET, test architect / lead. Drop intern / fresher / campus.
- Other-domain companies: keep only software-testing roles (SDET at Bosch), not factory QC.
- Detection: crawlers are caught by **tight loops**. Stages are separate CLI commands. Default crawl batch is small, shuffled, and delayed 15–45s between companies.
- Legal/safety: public listings only. Honor robots.txt. Stop and cool down on 401/403/429. No login, no CAPTCHA solving, no credential guessing, no proxy-evasion kit.

## Pipeline

1. `discover` — seed YAML + Wikipedia/Wikidata public APIs → `companies`
2. `resolve` — homepage → careers link → ATS fingerprint → `career_url`, `ats_kind`, `ats_slug`
3. `crawl` — polite fetch of that company's public jobs only
4. `filter` — in-process QA gate (no extra HTTP)
5. `transform` — experience, tech stack, domain
6. `save` — SQLite upserts keyed by `(company_id, source, external_id)`
7. `jobs` — query/export

## Files

- `pyproject.toml`, `src/jdscraper/**`, `tests/**`, `config/settings.yaml`, `config/companies.seed.yaml`
- `data/jdscraper.sqlite` (gitignored)

## Verification

- `uv run pytest tests/ -q` green
- `uv run jdscraper discover && uv run jdscraper crawl --limit 3` writes QA rows you can read back with `jdscraper jobs`

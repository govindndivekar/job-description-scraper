# Job Description Scraper

Find Bangalore employers and collect public QA / SDET / test-automation
job descriptions from their career pages into a local SQLite database.

This is complementary to `JobSearch` (job boards). This project walks
**company career pages**, not Naukri/LinkedIn SERPs.

## Why stages

Automatic crawlers get flagged by **request patterns**: same UA, fixed
interval, hundreds of hosts in a few minutes. The CLI is therefore split:

| Command | Network? | What it does |
|---|---|---|
| `discover` | Wikipedia/Wikidata only | Load the seed catalog and public company lists |
| `resolve` | One homepage per company | Find the careers URL and ATS type |
| `crawl` | One company at a time | Fetch public jobs, filter QA locally, save |
| `jobs` | No | Query the local database |

Default crawl batches are small, shuffled, and delayed 15–45 seconds
between companies. Official ATS JSON APIs are preferred over HTML.

## Setup

Ubuntu Python is PEP 668-locked. Use [uv](https://docs.astral.sh/uv/):

```bash
cd /home/govind_divekar/Projects/Hermes_Projects/JobDescriptionScrapper
uv sync --all-groups
```

## Run

From the repo root, after `uv sync --all-groups`. Global flags (`--settings`, `--db`) go before the subcommand.

```bash
uv run jdscraper --help
uv run jdscraper <command> --help
```

### Typical session

```bash
# 1. Load the seed catalog (and optional Wikipedia Bengaluru lists)
uv run jdscraper discover
uv run jdscraper discover --wikipedia --min-delay 1 --max-delay 2 --host-delay 1

# 2. Find career / ATS URLs for companies that still lack them
uv run jdscraper resolve --limit 10
uv run jdscraper resolve --company Okta

# 3. Fetch public jobs for a small shuffled batch (default 5)
uv run jdscraper crawl --limit 5
uv run jdscraper crawl --company Skillz --min-delay 4 --max-delay 6 --host-delay 7

# 4. Inspect what was saved
uv run jdscraper companies --limit 30
uv run jdscraper companies --source seed --limit 50
uv run jdscraper companies --json
uv run jdscraper jobs
uv run jdscraper jobs --company Okta
uv run jdscraper jobs --domain saas --json

# 5. Open the local viewer (http://127.0.0.1:8765)
uv run jdscraper serve
uv run jdscraper serve --host 127.0.0.1 --port 8765

# One-shot: discover + resolve + crawl one small batch
uv run jdscraper run --limit 5
uv run jdscraper run --limit 5 --wikipedia

# Tests
uv run pytest tests/ -q
```

### Commands

| Command | Default | What it does |
|---|---|---|
| `discover` | seed YAML only | Upsert companies from `config/companies.seed.yaml`. `--wikipedia` also pulls Bengaluru Wikipedia/Wikidata lists. `--seed PATH` overrides the seed file. |
| `resolve` | `--limit 10` | Visit homepage / careers links and detect ATS (Greenhouse, Lever, Ashby, Workday, …). `--company NAME` does one firm. |
| `crawl` | `--limit 5` | Fetch public jobs, keep Bangalore QA/SDET locally, upsert SQLite. `--company NAME` recrawls one firm even if recently done. |
| `companies` | `--limit 50` | List the employer catalog. `--source seed\|wikipedia`, `--json`. |
| `jobs` | all rows | List kept QA jobs. `--company NAME`, `--domain saas`, `--json`. |
| `serve` | `127.0.0.1:8765` | Local browser UI over the same SQLite file. `--host`, `--port`. |
| `run` | `--limit 5` | `discover` + `resolve` + `crawl` for one small batch. `--wikipedia` is optional. |

`--limit` caps how many companies that stage touches. Re-run later to continue. Already-crawled companies wait `recrawl_days` (default 7) unless you pass `--company`.

### Delay overrides (discover / resolve / crawl / run)

Defaults live in `config/settings.yaml` (15–45s between requests, 60s same-host cooldown). Tighten only for public APIs you already trust:

```bash
uv run jdscraper crawl --limit 3 --min-delay 4 --max-delay 8 --host-delay 10
```

| Flag | Meaning |
|---|---|
| `--min-delay SEC` | Floor between any two requests |
| `--max-delay SEC` | Ceiling; actual delay is jittered in the range |
| `--host-delay SEC` | Extra cooldown before hitting the same host again |

Do not drop these to zero against HTML career pages. ATS JSON APIs can use a few seconds.

## Cron

Three script-only jobs (no LLM) run on this machine:

| Job | IST | What |
|---|---|---|
| `jdscraper-resolve` | 10:00 | Seed upsert + resolve 8 companies |
| `jdscraper-crawl` | 19:00 | Crawl 5 due companies |
| `jdscraper-inspect` | 19:30 | Report new QA jobs / coverage; silent if unchanged |

They are staggered on purpose. There is no combined `run` cron.

See [DEPLOY-DIETPI.md](DEPLOY-DIETPI.md) to run this on a Raspberry Pi
with **system cron** (no Hermes). On this laptop the same three jobs
are Hermes script-only crons.

```bash
hermes cron list
hermes cron run d5e5680b691a    # fire resolve now
hermes cron pause ecc36a382686
```

## Viewer

```bash
uv run jdscraper serve
```

Opens a local app at `http://127.0.0.1:8765` against `data/jdscraper.sqlite`.
Tabs: Jobs, Companies, Coverage, Analysis.

To add an analysis later, register a function in `src/jdscraper/analysis/__init__.py`
(or call `register(Analysis(...))`). It shows up under Analysis with no UI change.

## What gets stored

Each kept job has: role, company, required experience, job description,
required tech stack, domain, location, source URL.

SQLite path: `data/jdscraper.sqlite` (gitignored).

## Rules

- Public listings only. Do not log in or solve CAPTCHAs.
- Stop on HTTP 401/403/429 and cool that host down.
- Honor robots.txt.
- Keep Bengaluru/Bangalore office or hybrid roles. Drop intern/fresher.
- At non-software companies, keep software-testing roles only.

# Deploy JobDescriptionScrapper on DietPi (Raspberry Pi 5)

This project is a **standalone Python CLI + SQLite + optional local web
UI**. It does **not** need Hermes Agent, a desktop, or a browser login.

WordPress on ports 80/443 is left alone. The viewer binds
`127.0.0.1:8765` only.

## Do you need Hermes on the Pi?

**No.** Skip Hermes on DietPi.

| Piece | Needs Hermes? | Needs a browser login? |
|---|---|---|
| `jdscraper discover / resolve / crawl / jobs` | No | No |
| Local viewer `jdscraper serve` | No | No |
| Daily cron (resolve / crawl / inspect) | No — use DietPi `crontab` | No |
| Hermes desktop / chat / xAI OAuth | Yes | Yes — this is what failed on the Pi |

Hermes setup opens a browser for provider OAuth (xAI, Google, …). A
headless Pi has nothing to complete that flow. Even if you finished
login, Hermes would only wrap the same `uv run jdscraper` commands.

Build and chat stay on your laptop. The Pi only runs the scraper.

## What you are installing

- Python 3.11+ (via `uv`, not DietPi system Python)
- This repo
- Three staggered cron jobs (same polite batches as the laptop)
- Optional systemd unit for the viewer
- Existing WordPress site: **untouched**

Hardware: Pi 5 4 GB+ is plenty. The crawler is I/O + sleep, not CPU.

---

## 0. On the laptop (before you SSH)

Decide how the Pi gets the code.

**A. Git clone** (repo is already on GitHub):

```text
https://github.com/govindndivekar/job-description-scraper.git
```

`data/jdscraper.sqlite` is gitignored. Either start a fresh DB on the
Pi (`discover` rebuilds the company catalog from
`config/companies.seed.yaml`) or copy the laptop DB if you want the
jobs already collected.

**B. Copy the laptop tree** (includes the live DB):

```bash
# on the laptop
rsync -av --exclude .venv --exclude __pycache__ --exclude .pytest_cache \
  /home/govind_divekar/Projects/Hermes_Projects/JobDescriptionScrapper/ \
  dietpi@PI_IP:apps/job-description-scraper/
```

Replace `dietpi` / `PI_IP` with your user and address.

---

## 1. SSH in and set the timezone

```bash
ssh dietpi@PI_IP
sudo timedatectl set-timezone Asia/Kolkata
timedatectl
# expect: Time zone: Asia/Kolkata (IST, +0530)
```

Cron uses the system timezone. IST keeps 10:00 / 19:00 aligned with
the laptop jobs.

---

## 2. Install only what the scraper needs

Do **not** install Chromium, Node, or Hermes.

```bash
sudo apt-get update
sudo apt-get install -y curl git ca-certificates
```

Install `uv` (official ARM64 Linux build — Pi 5 is aarch64):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv --version
```

`uv` will download its own CPython 3.11+ on first `uv sync`. You do
not need `dietpi-software` Python.

Confirm you are not fighting WordPress:

```bash
ss -ltn | grep -E ':80|:443|:8765' || true
# :80 / :443 = WordPress / web server. Leave them.
# :8765 should be free.
```

---

## 3. Put the project on disk

```bash
mkdir -p "$HOME/apps"
cd "$HOME/apps"
```

Git:

```bash
git clone https://github.com/govindndivekar/job-description-scraper.git
cd job-description-scraper
```

Or, if you rsync'd in step 0, `cd "$HOME/apps/job-description-scraper"`.

---

## 4. Create the virtualenv and verify

```bash
cd "$HOME/apps/job-description-scraper"
uv sync --all-groups
uv run pytest tests/ -q
uv run jdscraper --help
```

Expected: tests pass, help lists `discover resolve crawl jobs companies run serve`.

---

## 5. Load the company catalog

```bash
mkdir -p data
uv run jdscraper discover
```

This is local (YAML → SQLite). It does not hit the network.

Optional — bring the laptop DB instead of starting empty:

```bash
# on the laptop
scp /home/govind_divekar/Projects/Hermes_Projects/JobDescriptionScrapper/data/jdscraper.sqlite \
  dietpi@PI_IP:apps/job-description-scraper/data/
```

Then skip a second `discover` unless you also changed the seed file.

Check:

```bash
uv run jdscraper companies --limit 5
uv run jdscraper jobs
```

---

## 6. One polite smoke crawl (manual)

Do **not** run `jdscraper run` against hundreds of hosts. One small
batch:

```bash
uv run jdscraper resolve --limit 3
uv run jdscraper crawl --limit 2
uv run jdscraper jobs
```

Default delays are 15–45s between companies and 60s on the same host.
A 2-company crawl can take a few minutes. That is intentional.

If a host returns 401/403/429 the crawler stops that host. Do not
retry in a loop.

---

## 7. System cron (replaces Hermes cron)

Scripts live in the repo so they work without Hermes:

| Script | What |
|---|---|
| `scripts/cron/resolve.py` | `discover` + `resolve --limit 8` |
| `scripts/cron/crawl.py` | `crawl --limit 5` (silent) |
| `scripts/cron/inspect.py` | print new QA jobs / coverage; silent if unchanged |
| `scripts/cron/run.sh` | wrapper that logs under `data/logs/` |

```bash
chmod +x "$HOME/apps/job-description-scraper/scripts/cron/run.sh"
```

Dry-run the wrapper (inspect is safe and fast):

```bash
"$HOME/apps/job-description-scraper/scripts/cron/run.sh" inspect
tail -n 20 "$HOME/apps/job-description-scraper/data/logs/"inspect-*.log
```

Install crontab (**same user that owns the repo**, not root):

```bash
crontab -e
```

Paste (adjust the home path if your user is not `dietpi`):

```cron
SHELL=/bin/bash
PATH=/home/dietpi/.local/bin:/usr/local/bin:/usr/bin:/bin
MAILTO=""

# Staggered on purpose. Do not merge into one jdscraper run job.
0 10 * * * /home/dietpi/apps/job-description-scraper/scripts/cron/run.sh resolve
0 19 * * * /home/dietpi/apps/job-description-scraper/scripts/cron/run.sh crawl
30 19 * * * /home/dietpi/apps/job-description-scraper/scripts/cron/run.sh inspect
```

```bash
crontab -l
```

| When (IST) | Job |
|---|---|
| 10:00 | resolve 8 companies |
| 19:00 | crawl 5 due companies |
| 19:30 | inspect / log new QA jobs |

There is **no** combined `discover+resolve+crawl` cron. That burst is
how career-page crawlers get flagged.

DietPi note: `dietpi-cron` / `cron` must be enabled
(`systemctl is-active cron` → `active`). If it is off:

```bash
sudo systemctl enable --now cron
```

---

## 8. Optional: viewer as a systemd user service

The UI is useful on the LAN. It has **no password**. Bind localhost
only. Do not put it on port 80 next to WordPress.

```bash
mkdir -p "$HOME/.config/systemd/user"
cp "$HOME/apps/job-description-scraper/scripts/cron/jdscraper-viewer.service" \
  "$HOME/.config/systemd/user/"
```

Edit `WorkingDirectory` and `ExecStart` if your user is not `dietpi`:

```bash
nano "$HOME/.config/systemd/user/jdscraper-viewer.service"
```

```bash
loginctl enable-linger "$USER"          # keep it up after logout
systemctl --user daemon-reload
systemctl --user enable --now jdscraper-viewer
systemctl --user status jdscraper-viewer
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/
```

Open from your laptop through SSH, not the public WordPress vhost:

```bash
# on the laptop
ssh -N -L 8765:127.0.0.1:8765 dietpi@PI_IP
# browser: http://127.0.0.1:8765/
```

Do **not** reverse-proxy this onto the WordPress nginx/lighttpd site
unless you add your own auth first.

---

## 9. Optional: copy the laptop SQLite later

After more laptop crawls:

```bash
# stop the viewer if it has the file open
ssh dietpi@PI_IP 'systemctl --user stop jdscraper-viewer'
scp data/jdscraper.sqlite dietpi@PI_IP:apps/job-description-scraper/data/
ssh dietpi@PI_IP 'systemctl --user start jdscraper-viewer'
```

SQLite is a single file. Do not rsync it while a crawl is writing.

---

## 10. Keep WordPress isolated

| Service | Port | User |
|---|---|---|
| WordPress (lighttpd/nginx + PHP) | 80 / 443 | whatever DietPi installed |
| JDScraper viewer | **127.0.0.1:8765** | `dietpi` |
| JDScraper cron | none | `dietpi` crontab |

- Do not install this under `/var/www`.
- Do not run cron as `www-data`.
- Do not point a public DNS A record at `:8765`.
- Disk: SQLite + logs stay in `~/apps/job-description-scraper/data/`.

---

## 11. Operations cheat sheet

```bash
cd "$HOME/apps/job-description-scraper"

uv run jdscraper companies --limit 20
uv run jdscraper jobs
tail -n 50 data/logs/crawl-$(date +%Y%m).log
tail -n 50 data/logs/inspect-$(date +%Y%m).log

# pause crawling
crontab -e    # comment the 19:00 line

# one-off
./scripts/cron/run.sh resolve
```

Update code:

```bash
cd "$HOME/apps/job-description-scraper"
git pull
uv sync --all-groups
uv run pytest tests/ -q
```

---

## 12. What not to do

- Do not install Hermes on the Pi to “make cron work”.
- Do not run `jdscraper run --limit 200` or drop delays to 0.
- Do not crawl and resolve in the same hour.
- Do not log into career sites or solve CAPTCHAs.
- Do not expose `jdscraper serve` on the public WordPress vhost.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `uv: command not found` in cron | `PATH=` in crontab includes `/home/dietpi/.local/bin` |
| Cron never fires | `systemctl is-active cron`; `grep CRON /var/log/syslog` |
| Viewer down after reboot | `loginctl enable-linger`; `systemctl --user status jdscraper-viewer` |
| Permission denied on `data/` | repo owned by the same user as crontab |
| Tests fail on ARM | `uv python list`; need 3.11+. Re-run `uv sync --all-groups` |
| WordPress 502 after this | you bound something to :80 by mistake — stop it, leave WP alone |
| Hermes install still tempting | stay on the laptop; the Pi already has everything it needs |

#!/usr/bin/env bash
# Cron entrypoint. Usage: run.sh resolve|crawl|inspect
# resolve/crawl: sleep 5–40 min so HTTPS is not pinned to crontab :00.
# inspect: no sleep (SQLite only). Manual `python3 scripts/cron/*.py` has no jitter.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH}"
cd "$ROOT"
mkdir -p "$ROOT/data/logs"
cmd="${1:?usage: run.sh resolve|crawl|inspect}"
log="$ROOT/data/logs/${cmd}-$(date +%Y%m).log"
{
  echo "===== $(date -Iseconds) ${cmd} ====="
  if [ "$cmd" = "resolve" ] || [ "$cmd" = "crawl" ]; then
    delay=$((300 + RANDOM % 2101))
    echo "start jitter ${delay}s"
    sleep "$delay"
    echo "===== $(date -Iseconds) ${cmd} after jitter ====="
  fi
  python3 "$ROOT/scripts/cron/${cmd}.py"
} >>"$log" 2>&1

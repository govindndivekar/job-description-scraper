#!/usr/bin/env bash
# Cron entrypoint. Usage: run.sh resolve|crawl|inspect
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PATH="${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH}"
cd "$ROOT"
mkdir -p "$ROOT/data/logs"
cmd="${1:?usage: run.sh resolve|crawl|inspect}"
log="$ROOT/data/logs/${cmd}-$(date +%Y%m).log"
{
  echo "===== $(date -Iseconds) ${cmd} ====="
  python3 "$ROOT/scripts/cron/${cmd}.py"
} >>"$log" 2>&1

#!/usr/bin/env python3
"""Local discover + resolve --limit 8. Prints only when a career/ATS URL is new."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DB, run_jdscraper  # noqa: E402

LIMIT = 8


def snapshot() -> dict[str, tuple[str, str]]:
    if not DB.exists():
        return {}
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT name, career_url, ats_kind FROM companies").fetchall()
    conn.close()
    return {name: (career or "", ats or "") for name, career, ats in rows}


def main() -> int:
    before = snapshot()
    discovered = run_jdscraper(["discover"])
    if discovered.returncode != 0:
        sys.stderr.write(discovered.stderr or discovered.stdout)
        return discovered.returncode
    resolved = run_jdscraper(["resolve", "--limit", str(LIMIT)])
    if resolved.returncode != 0:
        sys.stderr.write(resolved.stderr or resolved.stdout)
        return resolved.returncode
    after = snapshot()
    gained = []
    for name, (career, ats) in after.items():
        old_career, old_ats = before.get(name, ("", ""))
        if career and not old_career:
            gained.append(f"{name}: {ats or 'generic'} {career}")
        elif ats and not old_ats:
            gained.append(f"{name}: ats={ats} {career}")
    if not gained:
        return 0
    print("JDScraper resolve")
    print(f"new career/ATS: {len(gained)}")
    for line in gained[:20]:
        print(line)
    if len(gained) > 20:
        print(f"... {len(gained) - 20} more")
    print(discovered.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

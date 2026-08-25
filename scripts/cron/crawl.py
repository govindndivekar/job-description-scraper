#!/usr/bin/env python3
"""Crawl --limit 5. Always silent on success; stderr on failure."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import run_jdscraper  # noqa: E402

LIMIT = 5


def main() -> int:
    result = run_jdscraper(["crawl", "--limit", str(LIMIT)])
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

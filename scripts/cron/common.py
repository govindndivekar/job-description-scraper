"""Shared paths for DietPi / laptop cron wrappers."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "jdscraper.sqlite"
STATE = ROOT / "data" / "cron_inspect_state.json"


def uv_bin() -> Path:
    found = shutil.which("uv")
    if found:
        return Path(found)
    home = Path.home() / ".local" / "bin" / "uv"
    if home.exists():
        return home
    raise FileNotFoundError("uv is not on PATH. Install https://docs.astral.sh/uv/")


def run_jdscraper(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    local_bin = str(Path.home() / ".local" / "bin")
    env["PATH"] = local_bin + os.pathsep + env.get("PATH", "")
    return subprocess.run(
        [str(uv_bin()), "run", "jdscraper", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

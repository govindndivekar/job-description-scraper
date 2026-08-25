from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class PoliteSettings:
    min_delay_seconds: float = 15
    max_delay_seconds: float = 45
    same_host_min_seconds: float = 60
    honor_robots: bool = True
    max_pages_per_company: int = 8
    timeout_seconds: float = 25
    stop_on_status: tuple[int, ...] = (401, 403, 429, 503)


@dataclass(slots=True)
class Settings:
    db_path: Path
    seed_path: Path
    city_required: bool
    recrawl_days: int
    user_agent: str
    locations: list[str]
    polite: PoliteSettings


def load_settings(path: str | Path | None = None) -> Settings:
    settings_path = Path(path) if path else ROOT / "config" / "settings.yaml"
    raw = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    polite_raw = raw.get("polite") or {}
    db_path = Path(raw.get("db_path") or "data/jdscraper.sqlite")
    seed_path = Path(raw.get("seed_path") or "config/companies.seed.yaml")
    if not db_path.is_absolute():
        db_path = ROOT / db_path
    if not seed_path.is_absolute():
        seed_path = ROOT / seed_path
    return Settings(
        db_path=db_path,
        seed_path=seed_path,
        city_required=bool(raw.get("city_required", True)),
        recrawl_days=int(raw.get("recrawl_days") or 7),
        user_agent=str(raw.get("user_agent") or "JDScraper/0.1"),
        locations=list(raw.get("locations") or ["Bengaluru", "Bangalore"]),
        polite=PoliteSettings(
            min_delay_seconds=float(polite_raw.get("min_delay_seconds", 15)),
            max_delay_seconds=float(polite_raw.get("max_delay_seconds", 45)),
            same_host_min_seconds=float(polite_raw.get("same_host_min_seconds", 60)),
            honor_robots=bool(polite_raw.get("honor_robots", True)),
            max_pages_per_company=int(polite_raw.get("max_pages_per_company", 8)),
            timeout_seconds=float(polite_raw.get("timeout_seconds", 25)),
            stop_on_status=tuple(int(x) for x in (polite_raw.get("stop_on_status") or [401, 403, 429, 503])),
        ),
    )

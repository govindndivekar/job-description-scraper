from __future__ import annotations

from pathlib import Path

import yaml

from jdscraper.models import Company


def load_seed(path: str | Path) -> list[Company]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    companies: list[Company] = []
    for item in payload.get("companies") or []:
        if not item.get("name"):
            continue
        companies.append(
            Company(
                name=str(item["name"]).strip(),
                website=str(item.get("website") or "").strip(),
                career_url=str(item.get("career_url") or "").strip(),
                domain=str(item.get("domain") or "").strip(),
                city=str(item.get("city") or "Bengaluru").strip(),
                ats_kind=str(item.get("ats_kind") or "").strip(),
                ats_slug=str(item.get("ats_slug") or "").strip(),
                ats_site=str(item.get("ats_site") or "").strip(),
                source=str(item.get("source") or "seed").strip(),
            )
        )
    return companies

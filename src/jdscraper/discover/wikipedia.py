from __future__ import annotations

import json
from typing import Iterable
from urllib.parse import urlencode

from jdscraper.fetch.polite import FetchResult, PoliteFetcher
from jdscraper.models import Company

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

CATEGORIES: tuple[tuple[str, str], ...] = (
    ("Category:Companies_based_in_Bengaluru", "software"),
    ("Category:Information_technology_companies_of_Bengaluru", "software"),
    ("Category:Manufacturing_companies_based_in_Bengaluru", "manufacturing"),
)

SKIP_PREFIXES = ("list of", "category:", "timeline of", "outline of", "talk:")


def _is_company_title(title: str) -> bool:
    lowered = title.lower().strip()
    if any(lowered.startswith(prefix) for prefix in SKIP_PREFIXES):
        return False
    if lowered.endswith("(disambiguation)"):
        return False
    return True


def wikipedia_members(fetcher: PoliteFetcher, category: str) -> list[str]:
    titles: list[str] = []
    cont = ""
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "page",
            "cmlimit": "100",
            "format": "json",
        }
        if cont:
            params["cmcontinue"] = cont
        result = fetcher.get(f"{WIKI_API}?{urlencode(params)}")
        if result.blocked or result.status >= 400 or not result.text:
            break
        try:
            payload = json.loads(result.text)
        except json.JSONDecodeError:
            break
        for member in payload.get("query", {}).get("categorymembers", []):
            title = member.get("title") or ""
            if _is_company_title(title):
                titles.append(title)
        cont = payload.get("continue", {}).get("cmcontinue") or ""
        if not cont:
            break
    return titles


def wikidata_websites(fetcher: PoliteFetcher, titles: Iterable[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    batch: list[str] = []

    def flush() -> None:
        if not batch:
            return
        params = {
            "action": "wbgetentities",
            "sites": "enwiki",
            "titles": "|".join(batch),
            "props": "claims|sitelinks",
            "format": "json",
        }
        result = fetcher.get(f"{WIKIDATA_API}?{urlencode(params)}")
        if result.blocked or result.status >= 400 or not result.text:
            batch.clear()
            return
        try:
            payload = json.loads(result.text)
        except json.JSONDecodeError:
            batch.clear()
            return
        for entity in (payload.get("entities") or {}).values():
            if not isinstance(entity, dict) or entity.get("missing") is not None:
                continue
            title = (entity.get("sitelinks") or {}).get("enwiki", {}).get("title")
            claims = entity.get("claims") or {}
            website = ""
            for claim in claims.get("P856") or []:
                try:
                    website = claim["mainsnak"]["datavalue"]["value"]
                    break
                except (KeyError, TypeError):
                    continue
            if title and website:
                mapping[title] = website
        batch.clear()

    for title in titles:
        batch.append(title)
        if len(batch) >= 20:
            flush()
    flush()
    return mapping


def companies_from_wikipedia(
    fetcher: PoliteFetcher,
    categories: tuple[tuple[str, str], ...] = CATEGORIES,
) -> list[Company]:
    found: dict[str, Company] = {}
    for category, domain in categories:
        for title in wikipedia_members(fetcher, category):
            if title not in found:
                found[title] = Company(name=title, domain=domain, city="Bengaluru", source="wikipedia")
            elif not found[title].domain:
                found[title].domain = domain
    websites = wikidata_websites(fetcher, found.keys())
    for title, website in websites.items():
        found[title].website = website
    return list(found.values())

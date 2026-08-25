#!/usr/bin/env python3
"""Validate Naukri seed rows and fill website / career_url via public APIs."""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "config" / "companies.seed.yaml"
CACHE = ROOT / "data" / "naukri_website_cache.json"
CACHE_VERSION = 2

STAFF_RE = re.compile(
    r"\b(staffing|recruitment|recruiter|manpower|placement|body[\s-]?shop)\b",
    re.I,
)
JUNK_RE = re.compile(
    r"^(confidential|client of|our client|naukri|dummy|test company|not disclosed)\b",
    re.I,
)
PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")
LEGAL_RE = re.compile(
    r"\b(pvt\.?|private|ltd\.?|limited|inc\.?|llc|llp|plc|gmbh|ag)\b",
    re.I,
)
STOP = {
    "pvt",
    "ltd",
    "limited",
    "inc",
    "llc",
    "llp",
    "the",
    "private",
    "co",
    "company",
}
GENERIC = {
    "research",
    "analytics",
    "health",
    "healthcare",
    "auto",
    "digital",
    "software",
    "systems",
    "solutions",
    "services",
    "media",
    "energy",
    "finance",
    "capital",
    "bank",
    "group",
    "global",
    "international",
    "india",
    "technologies",
    "technology",
    "tech",
    "labs",
    "lab",
    "data",
    "info",
    "consulting",
    "consultancy",
    "engineering",
    "airport",
    "hospital",
    "motors",
    "automotive",
}
BAD_HOSTS = {
    "facebook.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "wikipedia.org",
    "crunchbase.com",
    "naukri.com",
    "indeed.com",
    "glassdoor.com",
    "ambitionbox.com",
    "google.com",
    "play.google.com",
}
CURATED_ALIASES = {
    "tataadvancedsystems": "Tata Advanced Systems",
    "tataadvancedsystemstasl": "Tata Advanced Systems",
    "jpmorganchasebank": "JPMorgan Chase",
    "jpmorganchase": "JPMorgan Chase",
    "caterpillarinc": "Caterpillar",
    "tataconsultancyservices": "TCS",
    "advancedmicrodevicesamd": "AMD",
    "armembeddedtechnologies": "Arm",
    "marvellsemiconductors": "Marvell",
    "microchiptechnology": "Microchip",
    "mediatekindiatechnology": "MediaTek",
    "onsemiconductor": "onsemi",
}
MANUAL_URLS = {
    "Alpha Design Technologies": ("https://www.adtl.co.in", "https://www.adtl.co.in/careers"),
    "Ankit Fasteners": ("https://ankitgroup.com", "https://ankitgroup.com/careers"),
    "Park Controls & Communications": ("https://www.parkcontrols.com", "https://www.parkcontrols.com/careers"),
    "Fusion CX": ("https://www.fusioncx.com", "https://www.fusioncx.com/careers"),
    "Indo MIM": ("https://www.indo-mim.com", "https://www.indo-mim.com/careers"),
    "Mouser": ("https://www.mouser.com", "https://www.mouser.com/careers"),
    "Sapphire Foods": ("https://www.sapphirefoods.in", "https://www.sapphirefoods.in/careers"),
    "Attero Recycling": ("https://www.attero.in", "https://www.attero.in/careers"),
    "Shahi": ("https://shahi.co.in", "https://shahi.co.in/careers"),
    "Talentica": ("https://www.talentica.com", "https://www.talentica.com/careers"),
    "Nibav Lifts": ("https://www.nibavlifts.com", "https://www.nibavlifts.com/careers"),
    "Leap Finance": ("https://leapfinance.com", "https://leapfinance.com/careers"),
    "Cybrosys": ("https://www.cybrosys.com", "https://www.cybrosys.com/careers"),
    "Expleo": ("https://expleo.com", "https://expleo.com/careers"),
    "Trantor": ("https://www.trantorinc.com", "https://www.trantorinc.com/careers"),
    "Uniqus": ("https://uniqus.com", "https://uniqus.com/careers"),
    "Societe Generale Global Solution Centre": (
        "https://www.societegenerale.com",
        "https://careers.societegenerale.com",
    ),
}
UA = "JDScraper/0.1 (+personal job search; govind_divekar@yahoo.com)"


def tokens(name: str) -> set[str]:
    return {part for part in re.findall(r"[a-z0-9]+", name.lower()) if part not in STOP}


def norm_key(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def legal_stripped(name: str) -> str:
    cleaned = PAREN_RE.sub(" ", name)
    cleaned = LEGAL_RE.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip() or name.strip()


def host_of(domain: str) -> str:
    raw = domain.strip().lower()
    if "://" not in raw:
        raw = "https://" + raw
    host = urlparse(raw).netloc.removeprefix("www.")
    return host


def domain_related(company: str, domain: str, hit_name: str = "") -> bool:
    host = host_of(domain)
    stem = re.sub(r"[^a-z0-9]", "", host.split(".")[0])
    compact = re.sub(r"[^a-z0-9]", "", legal_stripped(company).lower())
    if not stem or not compact:
        return False
    if hit_name:
        name_ratio = SequenceMatcher(
            None, legal_stripped(company).lower(), legal_stripped(hit_name).lower()
        ).ratio()
        if name_ratio >= 0.82:
            return True
    if len(stem) <= 3:
        distinctive = [token for token in tokens(company) if len(token) >= 2]
        return compact == stem or (len(distinctive) == 1 and distinctive[0] == stem)
    if stem in compact or compact in stem:
        return True
    for token in tokens(company):
        if token in GENERIC or len(token) < 4:
            continue
        if token in stem or stem in token:
            return True
    return False


def score_candidate(company: str, hit_name: str, domain: str) -> float:
    host = host_of(domain)
    if not host or host in BAD_HOSTS or any(host.endswith("." + bad) for bad in BAD_HOSTS):
        return 0.0
    if not domain_related(company, host, hit_name):
        return 0.0
    left = legal_stripped(company).lower()
    right = legal_stripped(hit_name or host).lower()
    name_score = SequenceMatcher(None, left, right).ratio()
    qt, ht = tokens(company), tokens(hit_name or host)
    overlap = len(qt.intersection(ht)) / max(1, min(len(qt), len(ht))) if qt and ht else 0.0
    stem = re.sub(r"[^a-z0-9]", "", host.split(".")[0])
    compact = re.sub(r"[^a-z0-9]", "", left)
    domain_score = SequenceMatcher(None, compact[:20], stem[:20]).ratio()
    score = (0.45 * name_score) + (0.30 * overlap) + (0.25 * domain_score)
    extra = {token for token in ht if token not in qt and token not in GENERIC and len(token) >= 4}
    if extra:
        score -= 0.16 * min(2, len(extra))
    distinctive = [token for token in qt if token not in GENERIC]
    if len(distinctive) == 1 and len(distinctive[0]) <= 4:
        if stem not in {compact, distinctive[0]}:
            return 0.0
        if host.endswith(".com"):
            score += 0.05
        elif not (host.endswith(".in") or host.endswith(".co.in")):
            score -= 0.22
    if host.endswith(".in") or host.endswith(".co.in") or "india" in host:
        score += 0.06
    if host.endswith(".ie") or host.endswith(".co.uk") or host.endswith(".uk"):
        score -= 0.08
    return min(max(score, 0.0), 1.0)


def website_from_domain(domain: str) -> str:
    host = host_of(domain)
    return f"https://www.{host}" if host.count(".") == 1 else f"https://{host}"


def guess_career(website: str) -> str:
    parsed = urlparse(website)
    return f"{parsed.scheme}://{parsed.netloc}/careers"


def load_cache() -> dict:
    if not CACHE.exists():
        return {}
    payload = json.loads(CACHE.read_text())
    if payload.get("_version") != CACHE_VERSION:
        return {}
    payload.pop("_version", None)
    return payload


def save_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"_version": CACHE_VERSION, **cache}
    CACHE.write_text(json.dumps(payload, indent=2, sort_keys=True))


def clearbit_suggest(client: httpx.Client, query: str) -> list[dict]:
    response = client.get(
        "https://autocomplete.clearbit.com/v1/companies/suggest",
        params={"query": query},
        timeout=20,
    )
    if response.status_code != 200:
        return []
    payload = response.json()
    return payload if isinstance(payload, list) else []


def wikidata_website(client: httpx.Client, query: str) -> tuple[str, str] | None:
    search = client.get(
        "https://www.wikidata.org/w/api.php",
        params={
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "format": "json",
            "limit": 5,
            "type": "item",
        },
        timeout=25,
    )
    if search.status_code != 200:
        return None
    hits = (search.json().get("search") or [])[:3]
    if not hits:
        return None
    entities = client.get(
        "https://www.wikidata.org/w/api.php",
        params={
            "action": "wbgetentities",
            "ids": "|".join(hit["id"] for hit in hits),
            "props": "labels|claims",
            "languages": "en",
            "format": "json",
        },
        timeout=25,
    )
    if entities.status_code != 200:
        return None
    for entity in (entities.json().get("entities") or {}).values():
        mains = (entity.get("claims") or {}).get("P856") or []
        if not mains:
            continue
        value = mains[0].get("mainsnak", {}).get("datavalue", {}).get("value")
        label = ((entity.get("labels") or {}).get("en") or {}).get("value") or query
        if value:
            return value, label
    return None


def pick_best(company: str, candidates: list[tuple[str, str, str]]) -> dict | None:
    ranked = []
    for via, name, domain in candidates:
        score = score_candidate(company, name, domain)
        if score >= 0.68:
            ranked.append((score, via, name, domain))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked:
        return None
    score, via, name, domain = ranked[0]
    website = website_from_domain(domain)
    return {
        "website": website,
        "career_url": guess_career(website),
        "via": via,
        "score": round(score, 3),
        "matched_name": name,
        "domain": host_of(domain),
    }


def lookup_one(client: httpx.Client, name: str, cache: dict) -> dict:
    cached = cache.get(name)
    if cached and cached.get("version") == CACHE_VERSION:
        website = cached.get("website") or ""
        if not website:
            return cached
        if score_candidate(name, cached.get("matched_name") or "", cached.get("domain") or website) >= 0.68:
            return cached
        cache.pop(name, None)
    queries = []
    stripped = legal_stripped(name)
    for query in (name.strip(), stripped, f"{stripped} India"):
        if query and query not in queries:
            queries.append(query)
    candidates: list[tuple[str, str, str]] = []
    error = ""
    try:
        for query in queries:
            for hit in clearbit_suggest(client, query):
                domain = (hit.get("domain") or "").strip()
                if domain:
                    candidates.append(("clearbit", hit.get("name") or query, domain))
            picked_so_far = pick_best(name, candidates)
            if picked_so_far and picked_so_far["score"] >= 0.85:
                break
        if not pick_best(name, candidates):
            wiki = wikidata_website(client, stripped)
            if wiki:
                url, label = wiki
                candidates.append(("wikidata", label, host_of(url)))
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    picked = pick_best(name, candidates) or {
        "website": "",
        "career_url": "",
        "via": "",
        "score": 0,
        "matched_name": "",
        "domain": "",
    }
    result = {
        "query": stripped,
        "error": error,
        "version": CACHE_VERSION,
        **picked,
    }
    cache[name] = result
    return result


def analyze(companies: list[dict]) -> dict:
    naukri = [c for c in companies if str(c.get("source", "")).lower() == "naukri"]
    seeded = [c for c in companies if str(c.get("source", "")).lower() != "naukri"]
    seed_keys = {norm_key(c["name"]): c["name"] for c in seeded}
    seed_keys.update({key: label for key, label in CURATED_ALIASES.items() if key in seed_keys or True})
    # aliases point at curated labels; mark overlap when alias key matches
    internal = []
    seen: dict[str, str] = {}
    overlaps = []
    staffing = []
    junk = []
    for company in naukri:
        key = norm_key(company["name"])
        if key in seen:
            internal.append((seen[key], company["name"]))
        else:
            seen[key] = company["name"]
        if key in {norm_key(c["name"]) for c in seeded} or key in CURATED_ALIASES:
            overlaps.append((company["name"], seed_keys.get(key) or CURATED_ALIASES.get(key)))
        if STAFF_RE.search(company["name"]):
            staffing.append(company["name"])
        if JUNK_RE.search(company["name"]):
            junk.append(company["name"])
    return {
        "naukri": len(naukri),
        "seeded": len(seeded),
        "missing_website": sum(1 for c in naukri if not c.get("website")),
        "missing_career": sum(1 for c in naukri if not c.get("career_url")),
        "internal_dupes": internal,
        "curated_overlaps": overlaps,
        "staffing": staffing,
        "junk": junk,
        "no_domain": [c["name"] for c in naukri if not c.get("domain")],
        "domains": Counter(c.get("domain") or "unknown" for c in naukri),
    }


def drop_names() -> set[str]:
    return {
        "Naukri",
        "Naukri E Hire Campaign",
        "Naukri E-hire",
        "Naukri Assist",
        "Indo- Mim",
        "Tata Advanced Systems (TASL)",
        "JPMorgan Chase Bank",
        "Caterpillar Inc",
        "Tata Consultancy Services",
        "Advanced Micro Devices (AMD)",
        "ARM Embedded Technologies",
        "Marvell Semiconductors",
        "Microchip Technology",
        "Mediatek India Technology",
        "ON Semiconductor",
    }


def patch_yaml(text: str, updates: dict[str, dict]) -> str:
    drop = drop_names()
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    naukri_mode = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("  # --- Naukri"):
            naukri_mode = True
        match = re.match(r"^  - name: (.+)\n$", line)
        if naukri_mode and match:
            name = match.group(1).strip()
            block = [line]
            i += 1
            while i < len(lines) and not re.match(r"^  - name: ", lines[i]) and not lines[i].startswith("  # ---"):
                block.append(lines[i])
                i += 1
            blob = "".join(block)
            if name in drop:
                continue
            if "source: naukri" in blob:
                hit = updates.get(name)
                if hit and hit.get("website") and "website:" not in blob:
                    insert = f"    website: {hit['website']}\n    career_url: {hit['career_url']}\n"
                    block = [block[0], insert, *block[1:]]
            out.extend(block)
            continue
        out.append(line)
        i += 1
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.12)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--write-only", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--names", help="Comma-separated names to look up")
    args = parser.parse_args()

    raw = SEED.read_text(encoding="utf-8")
    companies = (yaml.safe_load(raw) or {}).get("companies") or []
    report = analyze(companies)
    print(
        json.dumps(
            {
                "naukri": report["naukri"],
                "seeded": report["seeded"],
                "missing_website": report["missing_website"],
                "internal_dupes": report["internal_dupes"],
                "curated_overlaps": report["curated_overlaps"],
                "staffing": report["staffing"],
                "junk": report["junk"],
                "no_domain_count": len(report["no_domain"]),
            },
            indent=2,
        )
    )
    if args.analyze_only:
        return 0

    cache = load_cache()
    found = 0
    looked = 0
    if not args.write_only:
        if args.names:
            wanted = {item.strip() for item in args.names.split(",") if item.strip()}
            naukri = [{"name": name} for name in wanted]
        else:
            naukri = [
                c
                for c in companies
                if str(c.get("source", "")).lower() == "naukri" and not c.get("website")
            ]
        if args.limit:
            naukri = naukri[: args.limit]
        looked = len(naukri)
        for company in naukri:
            cached = cache.get(company["name"])
            if not cached:
                continue
            website = cached.get("website") or ""
            if website and score_candidate(
                company["name"], cached.get("matched_name") or "", cached.get("domain") or website
            ) < 0.68:
                cache.pop(company["name"], None)
        pending = [c for c in naukri if c["name"] not in cache]
        found = sum(1 for c in naukri if (cache.get(c["name"]) or {}).get("website"))
        print(f"pending={len(pending)} already_cached={looked - len(pending)} cached_hits={found}", flush=True)
        lock = threading.Lock()

        def work(company: dict) -> tuple[str, dict]:
            with httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"}, follow_redirects=True) as client:
                result = lookup_one(client, company["name"], {})
            time.sleep(args.delay)
            return company["name"], result

        done = 0
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = [pool.submit(work, company) for company in pending]
            for future in as_completed(futures):
                name, result = future.result()
                with lock:
                    cache[name] = result
                    done += 1
                    if result.get("website"):
                        found += 1
                    if done % 20 == 0 or done == len(pending):
                        save_cache(cache)
                        print(f"progress {done}/{len(pending)} found={found}", flush=True)
        save_cache(cache)
    updates = {}
    for name, row in cache.items():
        if not isinstance(row, dict) or not row.get("website"):
            continue
        if score_candidate(name, row.get("matched_name") or "", row.get("domain") or row["website"]) < 0.68:
            continue
        updates[name] = row
    for name, (website, career) in MANUAL_URLS.items():
        updates[name] = {"website": website, "career_url": career, "via": "manual", "score": 1.0}
    print(f"looked_up={looked} cache_with_website={len(updates)} batch_found={found}")
    if args.write or args.write_only:
        SEED.write_text(patch_yaml(raw, updates), encoding="utf-8")
        print(f"wrote {SEED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

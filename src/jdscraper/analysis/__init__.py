from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable

from jdscraper.db import JobStore

Runner = Callable[[JobStore], dict]


@dataclass(frozen=True, slots=True)
class Analysis:
    name: str
    title: str
    description: str
    run: Runner


def _stack_demand(store: JobStore) -> dict:
    counts: Counter = Counter()
    for job in store.list_jobs():
        counts.update(job.tech_stack)
    total = sum(counts.values()) or 1
    rows = [
        {"label": name, "value": count, "share": round(count / total, 3)}
        for name, count in counts.most_common()
    ]
    return {
        "summary": f"{len(rows)} tools across {sum(counts.values())} mentions.",
        "rows": rows,
    }


def _experience_bands(store: JobStore) -> dict:
    bands = (("0-4", 0, 4), ("5-8", 5, 8), ("9-12", 9, 12), ("13+", 13, 99), ("unspecified", None, None))
    counts: Counter = Counter()
    for job in store.list_jobs():
        years = job.years_min
        if years is None:
            counts["unspecified"] += 1
            continue
        placed = False
        for label, lo, hi in bands:
            if lo is None:
                continue
            if lo <= years <= hi:
                counts[label] += 1
                placed = True
                break
        if not placed:
            counts["13+"] += 1
    total = sum(counts.values()) or 1
    rows = [
        {"label": label, "value": counts[label], "share": round(counts[label] / total, 3)}
        for label, _, _ in bands
        if counts[label]
    ]
    return {"summary": f"{sum(counts.values())} jobs grouped by minimum years.", "rows": rows}


def _domain_coverage(store: JobStore) -> dict:
    companies = store.list_companies()
    jobs = store.list_jobs()
    job_domains = Counter(job.domain or "unknown" for job in jobs)
    company_domains = Counter(company.domain or "unknown" for company in companies)
    rows = []
    for domain, company_count in company_domains.most_common():
        rows.append(
            {
                "label": domain,
                "value": job_domains.get(domain, 0),
                "share": round(company_count / (len(companies) or 1), 3),
                "companies": company_count,
            }
        )
    return {
        "summary": f"{len(companies)} employers across {len(company_domains)} domains.",
        "rows": rows,
    }


REGISTRY: dict[str, Analysis] = {
    "stack-demand": Analysis(
        name="stack-demand",
        title="Stack demand",
        description="How often each tool appears in kept QA / SDET descriptions.",
        run=_stack_demand,
    ),
    "experience-bands": Analysis(
        name="experience-bands",
        title="Experience bands",
        description="Minimum years requested, grouped into bands.",
        run=_experience_bands,
    ),
    "domain-coverage": Analysis(
        name="domain-coverage",
        title="Domain coverage",
        description="Catalog size versus jobs found in each industry domain.",
        run=_domain_coverage,
    ),
}


def register(analysis: Analysis) -> None:
    REGISTRY[analysis.name] = analysis


def list_analyses() -> list[dict]:
    return [
        {"name": item.name, "title": item.title, "description": item.description}
        for item in REGISTRY.values()
    ]


def get_analysis(name: str) -> Analysis | None:
    return REGISTRY.get(name)


def run_analysis(name: str, store: JobStore) -> dict:
    analysis = REGISTRY[name]
    payload = analysis.run(store)
    payload["name"] = analysis.name
    payload["title"] = analysis.title
    payload["description"] = analysis.description
    return payload

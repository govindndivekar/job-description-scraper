from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from jdscraper.careers.resolver import resolve_company
from jdscraper.config import Settings, load_settings
from jdscraper.crawl import fetch_company_jobs
from jdscraper.db import JobStore
from jdscraper.discover.seed import load_seed
from jdscraper.fetch.http import HttpxTransport
from jdscraper.fetch.polite import PoliteFetcher, PolitePolicy
from jdscraper.pipeline import ingest_raw_jobs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bangalore QA/SDET career-page scraper")
    parser.add_argument("--settings", help="Path to settings YAML")
    parser.add_argument("--db", help="SQLite path override")
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser("discover", help="Load seed companies (and optional Wikipedia lists)")
    discover.add_argument("--seed", help="Seed YAML override")
    discover.add_argument("--wikipedia", action="store_true", help="Also pull Bengaluru company categories")
    _add_delay_flags(discover)

    resolve = sub.add_parser("resolve", help="Find career URLs / ATS type for companies missing them")
    resolve.add_argument("--limit", type=int, default=10)
    resolve.add_argument("--company", help="Resolve one company by name")
    _add_delay_flags(resolve)

    crawl = sub.add_parser("crawl", help="Fetch public jobs for a small shuffled company batch")
    crawl.add_argument("--limit", type=int, default=5)
    crawl.add_argument("--company", help="Crawl one company by name")
    _add_delay_flags(crawl)

    jobs = sub.add_parser("jobs", help="List stored QA jobs")
    jobs.add_argument("--json", action="store_true")
    jobs.add_argument("--domain", help="Filter by domain")
    jobs.add_argument("--company", help="Filter by company name")

    companies = sub.add_parser("companies", help="List catalogued Bangalore employers")
    companies.add_argument("--json", action="store_true")
    companies.add_argument("--source", help="Filter seed or wikipedia")
    companies.add_argument("--limit", type=int, default=50)

    run = sub.add_parser("run", help="discover + resolve + crawl one small batch")
    run.add_argument("--limit", type=int, default=5)
    run.add_argument("--wikipedia", action="store_true")
    _add_delay_flags(run)

    serve = sub.add_parser("serve", help="Open the local browser viewer")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def _add_delay_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--min-delay", type=float, help="Override min delay seconds")
    parser.add_argument("--max-delay", type=float, help="Override max delay seconds")
    parser.add_argument("--host-delay", type=float, help="Override same-host cooldown seconds")


def _settings(args) -> Settings:
    settings = load_settings(args.settings)
    if getattr(args, "db", None):
        settings.db_path = Path(args.db)
    return settings


def _flag(args, name: str, default):
    value = getattr(args, name, None)
    return default if value is None else value


def _policy(settings: Settings, args) -> PolitePolicy:
    polite = settings.polite
    return PolitePolicy(
        min_delay_seconds=float(_flag(args, "min_delay", polite.min_delay_seconds)),
        max_delay_seconds=float(_flag(args, "max_delay", polite.max_delay_seconds)),
        same_host_min_seconds=float(_flag(args, "host_delay", polite.same_host_min_seconds)),
        honor_robots=polite.honor_robots,
        timeout_seconds=polite.timeout_seconds,
        stop_on_status=polite.stop_on_status,
        user_agent=settings.user_agent,
    )


def _fetcher(settings: Settings, args) -> PoliteFetcher:
    policy = _policy(settings, args)
    transport = HttpxTransport(policy)
    return PoliteFetcher(
        policy=policy,
        transport=transport,
        rng=random.Random(),
        post_transport=transport.post,
    )


def cmd_discover(args) -> int:
    settings = _settings(args)
    store = JobStore(settings.db_path)
    seed_path = Path(args.seed) if args.seed else settings.seed_path
    companies = load_seed(seed_path)
    for company in companies:
        store.upsert_company(company)
    extra = 0
    if args.wikipedia:
        from jdscraper.discover.wikipedia import companies_from_wikipedia

        fetcher = _fetcher(settings, args)
        for company in companies_from_wikipedia(fetcher):
            store.upsert_company(company)
            extra += 1
    print(f"catalog={store.company_count()} seed={len(companies)} wikipedia={extra} db={settings.db_path}")
    store.close()
    return 0


def cmd_resolve(args) -> int:
    settings = _settings(args)
    store = JobStore(settings.db_path)
    fetcher = _fetcher(settings, args)
    if args.company:
        target = store.get_company(args.company)
        companies = [target] if target else []
        if not companies:
            print(f"unknown company: {args.company}", file=sys.stderr)
            return 1
    else:
        companies = store.unresolved_companies()[: args.limit]
    random.shuffle(companies)
    resolved = 0
    for company in companies:
        updated = resolve_company(company, fetcher)
        store.upsert_company(updated)
        print(f"{updated.name}: ats={updated.ats_kind or '-'} {updated.career_url or '-'}")
        if updated.career_url:
            resolved += 1
    print(f"resolved={resolved}/{len(companies)}")
    store.close()
    return 0


def cmd_crawl(args) -> int:
    settings = _settings(args)
    store = JobStore(settings.db_path)
    fetcher = _fetcher(settings, args)
    if args.company:
        target = store.get_company(args.company)
        companies = [target] if target else []
        if not companies:
            print(f"unknown company: {args.company}", file=sys.stderr)
            return 1
    else:
        companies = store.due_companies(recrawl_days=settings.recrawl_days)
        random.shuffle(companies)
        companies = companies[: args.limit]
    saved = 0
    for company in companies:
        raw, status = fetch_company_jobs(company, fetcher)
        kept = ingest_raw_jobs(store, company, raw) if status == "ok" else []
        store.mark_crawled(company.id, status)  # type: ignore[arg-type]
        print(f"{company.name}: raw={len(raw)} kept={len(kept)} status={status}")
        saved += len(kept)
    print(f"saved={saved} companies={len(companies)} db={settings.db_path}")
    store.close()
    return 0


def cmd_jobs(args) -> int:
    settings = _settings(args)
    store = JobStore(settings.db_path)
    rows = store.list_jobs()
    if args.domain:
        rows = [job for job in rows if job.domain.lower() == args.domain.lower()]
    if args.company:
        rows = [job for job in rows if job.company_name.lower() == args.company.lower()]
    if args.json:
        payload = [
            {
                "role": job.role,
                "company": job.company_name,
                "years_min": job.years_min,
                "years_max": job.years_max,
                "description": job.description,
                "tech_stack": job.tech_stack,
                "domain": job.domain,
                "location": job.location,
                "url": job.url,
            }
            for job in rows
        ]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if not rows:
            print("no jobs stored yet")
        for job in rows:
            years = (
                f"{job.years_min}-{job.years_max}"
                if job.years_min is not None and job.years_max is not None
                else (f"{job.years_min}+" if job.years_min is not None else "?")
            )
            stack = ", ".join(job.tech_stack[:6])
            print(f"{job.role} | {job.company_name} | {years} yrs | {job.domain} | {stack} | {job.url}")
    store.close()
    return 0


def cmd_companies(args) -> int:
    settings = _settings(args)
    store = JobStore(settings.db_path)
    rows = store.list_companies()
    if args.source:
        rows = [company for company in rows if company.source.lower() == args.source.lower()]
    print(f"companies={len(rows)}")
    shown = rows[: args.limit]
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "name": company.name,
                        "website": company.website,
                        "career_url": company.career_url,
                        "ats_kind": company.ats_kind,
                        "domain": company.domain,
                        "source": company.source,
                    }
                    for company in shown
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        for company in shown:
            print(
                f"{company.name} | {company.domain or '-'} | {company.ats_kind or '-'} | "
                f"{company.career_url or company.website or '-'} | {company.source}"
            )
        if len(rows) > len(shown):
            print(f"... {len(rows) - len(shown)} more (raise --limit)")
    store.close()
    return 0


def cmd_run(args) -> int:
    discover_ns = argparse.Namespace(
        settings=args.settings,
        db=args.db,
        seed=None,
        wikipedia=args.wikipedia,
        min_delay=getattr(args, "min_delay", None),
        max_delay=getattr(args, "max_delay", None),
        host_delay=getattr(args, "host_delay", None),
    )
    cmd_discover(discover_ns)
    resolve_ns = argparse.Namespace(
        settings=args.settings,
        db=args.db,
        limit=args.limit,
        company=None,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        host_delay=args.host_delay,
    )
    cmd_resolve(resolve_ns)
    crawl_ns = argparse.Namespace(
        settings=args.settings,
        db=args.db,
        limit=args.limit,
        company=None,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        host_delay=args.host_delay,
    )
    return cmd_crawl(crawl_ns)


def cmd_serve(args) -> int:
    from jdscraper.serve import run_server

    settings = _settings(args)
    httpd = run_server(args.host, args.port, settings.db_path)
    url = f"http://{args.host}:{args.port}/"
    print(f"viewer {url}")
    print(f"db {settings.db_path}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    commands = {
        "discover": cmd_discover,
        "resolve": cmd_resolve,
        "crawl": cmd_crawl,
        "jobs": cmd_jobs,
        "companies": cmd_companies,
        "run": cmd_run,
        "serve": cmd_serve,
    }
    raise SystemExit(commands[args.command](args))


if __name__ == "__main__":
    main()

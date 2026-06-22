import json

import typer

from . import __version__

app = typer.Typer(help="Lead Machine worker", no_args_is_help=True)


@app.command()
def hello() -> None:
    """Smoke test: confirm the worker runs."""
    typer.echo(f"lead-machine worker {__version__} — ok")


@app.command()
def health() -> None:
    """Check connectivity to Supabase (requires env)."""
    from .db import get_client

    client = get_client()
    res = client.table("leads").select("id", count="exact").limit(1).execute()
    typer.echo(f"supabase ok — leads count: {res.count}")


@app.command()
def categories() -> None:
    """List the branchekode catalog (grouped) as JSON."""
    from .cvr.branchekoder import GROUPS, grouped

    out = {
        group: {
            "label": GROUPS.get(group, group),
            "branches": [
                {"code": b.code, "db07": b.code_db07, "label_da": b.label_da}
                for b in branches
            ],
        }
        for group, branches in grouped().items()
    }
    typer.echo(json.dumps(out, ensure_ascii=False, indent=2))


@app.command()
def discover(
    search_id: str = typer.Option(
        None, "--search-id", help="Run a saved search row (loads its parameters)."
    ),
    branchekode: list[str] = typer.Option(
        None, "--branchekode", "-b", help="Branchekode(s); repeatable. Used if no --search-id."
    ),
    postnr: list[int] = typer.Option(
        None, "--postnr", "-p", help="Postal code(s); repeatable."
    ),
    band: list[str] = typer.Option(
        None, "--band", help="Employee interval band(s), e.g. ANTAL_2_4; repeatable."
    ),
) -> None:
    """Run CVR discovery and upsert leads (requires Supabase + CVR creds)."""
    from .config import settings
    from .cvr import EsCvrClient, SearchParameters, SupabaseLeadWriter, run_discovery
    from .db import get_client

    db = get_client()

    if search_id:
        res = db.table("searches").select("parameters").eq("id", search_id).single().execute()
        params = SearchParameters.model_validate(res.data["parameters"] or {})
    else:
        params = SearchParameters(
            branchekoder=branchekode or [],
            postnumre=postnr or [],
            employee_bands=band or [],
        )

    writer = SupabaseLeadWriter(db)
    with EsCvrClient.from_settings(settings) as client:
        if search_id:
            db.table("searches").update({"status": "running"}).eq("id", search_id).execute()
        stats = run_discovery(client, params, writer, search_id=search_id)
        if search_id:
            db.table("searches").update(
                {"status": "completed", "stats": stats.as_dict()}
            ).eq("id", search_id).execute()

    typer.echo(json.dumps(stats.as_dict(), indent=2))


@app.command(name="enrich-financial")
def enrich_financial(
    limit: int = typer.Option(200, help="Max leads to enrich in this run."),
) -> None:
    """Attach XBRL financials + revenue estimate + CVR contacts to leads."""
    from .config import settings
    from .db import get_client
    from .financial import (
        FinancialClient,
        SupabaseFinancialWriter,
        run_financial_enrichment,
    )
    from .financial.models import LeadToEnrich

    db = get_client()
    res = (
        db.table("leads")
        .select("id,cvr_number,branchekode,employees_exact,employees_band,lead_enrichment(cvr)")
        .not_.is_("cvr_number", "null")
        .limit(limit)
        .execute()
    )

    leads = []
    for row in res.data or []:
        enr = row.get("lead_enrichment")
        if isinstance(enr, list):
            enr = enr[0] if enr else None
        leads.append(
            LeadToEnrich(
                lead_id=row["id"],
                cvr_number=row["cvr_number"],
                branchekode=row.get("branchekode"),
                employees_exact=row.get("employees_exact"),
                employees_band=row.get("employees_band"),
                raw_cvr=(enr or {}).get("cvr") if enr else None,
            )
        )

    writer = SupabaseFinancialWriter(db)
    with FinancialClient.from_settings(settings) as client:
        stats = run_financial_enrichment(leads, client, writer)

    typer.echo(json.dumps(stats.as_dict(), indent=2))


@app.command()
def qualify(
    limit: int = typer.Option(200, help="Max leads to qualify in this run."),
    only_unknown: bool = typer.Option(True, help="Only leads whose website_need is still unknown."),
) -> None:
    """Classify each lead's website_need (no/dead/parked/facebook/bad/...)."""
    from .config import settings
    from .db import get_client
    from .website import (
        DnsResolver,
        HttpxFetcher,
        PageSpeedClient,
        SupabaseWebsiteWriter,
        WebsiteDeps,
        run_qualification,
    )
    from .website.models import LeadToQualify

    db = get_client()
    query = db.table("leads").select("id,website").not_.is_("cvr_number", "null")
    if only_unknown:
        query = query.eq("website_need", "unknown")
    res = query.limit(limit).execute()
    leads = [LeadToQualify(lead_id=r["id"], website=r.get("website")) for r in (res.data or [])]

    psi = PageSpeedClient.from_settings(settings) if settings.pagespeed_api_key else None
    fetcher = HttpxFetcher()
    try:
        deps = WebsiteDeps(fetcher=fetcher, resolver=DnsResolver(), pagespeed=psi)
        stats = run_qualification(leads, deps, SupabaseWebsiteWriter(db))
    finally:
        fetcher.close()
        if psi is not None:
            psi.close()

    typer.echo(json.dumps(stats.as_dict(), indent=2))


@app.command()
def score(
    limit: int = typer.Option(500, help="Max leads to score in this run."),
    only_qualified: bool = typer.Option(
        True, help="Only leads whose website_need has been determined (skip 'unknown')."
    ),
) -> None:
    """Compute the 0–100 website-selling score + ranked breakdown for each lead."""
    from .db import get_client
    from .scoring import LeadToScore, SupabaseScoreWriter, Weights, run_scoring

    db = get_client()

    criteria = db.table("scoring_criteria").select("key,weight,config,is_active").execute()
    weights = Weights.from_criteria(criteria.data or [])

    query = db.table("leads").select(
        "id,website_need,branchekode,employees_band,employees_exact,founded_at,"
        "cvr_status,reklamebeskyttet,lead_enrichment(website,social,financial)"
    )
    if only_qualified:
        query = query.neq("website_need", "unknown")
    res = query.limit(limit).execute()

    leads = []
    for row in res.data or []:
        enr = row.get("lead_enrichment")
        if isinstance(enr, list):
            enr = enr[0] if enr else None
        enr = enr or {}
        leads.append(
            LeadToScore(
                lead_id=row["id"],
                website_need=row.get("website_need") or "unknown",
                branchekode=row.get("branchekode"),
                employees_band=row.get("employees_band"),
                employees_exact=row.get("employees_exact"),
                founded_at=row.get("founded_at"),
                cvr_status=row.get("cvr_status"),
                reklamebeskyttet=bool(row.get("reklamebeskyttet")),
                website=enr.get("website") or {},
                social=enr.get("social") or {},
                financial=enr.get("financial") or {},
            )
        )

    stats = run_scoring(leads, SupabaseScoreWriter(db), weights=weights)
    typer.echo(json.dumps(stats.as_dict(), indent=2))


if __name__ == "__main__":
    app()

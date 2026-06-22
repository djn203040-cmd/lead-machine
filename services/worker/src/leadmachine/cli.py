import json
from typing import Any

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
    from .jobs import JobRun

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
    with JobRun(db, "discover", search_id=search_id) as job:
        with EsCvrClient.from_settings(settings) as client:
            if search_id:
                db.table("searches").update({"status": "running"}).eq("id", search_id).execute()
            stats = run_discovery(client, params, writer, search_id=search_id)
            if search_id:
                db.table("searches").update(
                    {"status": "completed", "stats": stats.as_dict()}
                ).eq("id", search_id).execute()
        job.result = stats.as_dict()

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
    from .jobs import JobRun

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
    with JobRun(db, "enrich-financial", payload={"limit": limit}) as job:
        with FinancialClient.from_settings(settings) as client:
            stats = run_financial_enrichment(leads, client, writer)
        job.result = stats.as_dict()

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
    from .jobs import JobRun

    db = get_client()
    query = db.table("leads").select("id,website").not_.is_("cvr_number", "null")
    if only_unknown:
        query = query.eq("website_need", "unknown")
    res = query.limit(limit).execute()
    leads = [LeadToQualify(lead_id=r["id"], website=r.get("website")) for r in (res.data or [])]

    psi = PageSpeedClient.from_settings(settings) if settings.pagespeed_api_key else None
    fetcher = HttpxFetcher()
    with JobRun(db, "qualify", payload={"limit": limit, "only_unknown": only_unknown}) as job:
        try:
            deps = WebsiteDeps(fetcher=fetcher, resolver=DnsResolver(), pagespeed=psi)
            stats = run_qualification(leads, deps, SupabaseWebsiteWriter(db))
        finally:
            fetcher.close()
            if psi is not None:
                psi.close()
        job.result = stats.as_dict()

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
    from .jobs import JobRun
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

    with JobRun(db, "score", payload={"limit": limit, "only_qualified": only_qualified}) as job:
        stats = run_scoring(leads, SupabaseScoreWriter(db), weights=weights)
        job.result = stats.as_dict()
    typer.echo(json.dumps(stats.as_dict(), indent=2))


@app.command()
def angles(
    limit: int = typer.Option(100, help="Max leads to generate angles for in this run."),
    only_missing: bool = typer.Option(
        True, help="Skip leads that already have a generated angle."
    ),
) -> None:
    """Generate Danish phone-call sales angles with Claude (requires ANTHROPIC_API_KEY)."""
    from .angles import ClaudeAnglesClient, SupabaseAngleWriter, run_angles
    from .angles.models import LeadForAngle
    from .config import settings
    from .db import get_client
    from .financial.estimate import band_midpoint
    from .jobs import JobRun

    db = get_client()
    res = (
        db.table("leads")
        .select(
            "id,company_name,city,branche_text,website_need,employees_band,employees_exact,"
            "score,lead_enrichment(website,social,financial),lead_scores(breakdown),"
            "lead_angles(lead_id)"
        )
        .neq("website_need", "unknown")
        .limit(limit)
        .execute()
    )

    def _one(value: Any) -> Any:
        return (value[0] if value else None) if isinstance(value, list) else value

    leads = []
    for row in res.data or []:
        if only_missing and _one(row.get("lead_angles")):
            continue
        enr = _one(row.get("lead_enrichment")) or {}
        scores = _one(row.get("lead_scores")) or {}
        leads.append(
            LeadForAngle(
                lead_id=row["id"],
                company_name=row["company_name"],
                city=row.get("city"),
                branche_text=row.get("branche_text"),
                website_need=row.get("website_need") or "unknown",
                employees=row.get("employees_exact") or band_midpoint(row.get("employees_band")),
                score=row.get("score"),
                website=enr.get("website") or {},
                financial=enr.get("financial") or {},
                social=enr.get("social") or {},
                score_breakdown=scores.get("breakdown") or {},
            )
        )

    with JobRun(db, "angles", payload={"limit": limit, "only_missing": only_missing}) as job:
        with ClaudeAnglesClient.from_settings(settings) as client:
            stats = run_angles(leads, client, SupabaseAngleWriter(db))
        job.result = stats.as_dict()

    typer.echo(json.dumps(stats.as_dict(), indent=2))


@app.command()
def screen(
    limit: int = typer.Option(1000, help="Max sole-trader leads to screen in this run."),
) -> None:
    """Screen sole-trader leads against the Robinson opt-out list (compliance gate).

    Loads the register from ``ROBINSON_LIST_PATH`` and flags any matched lead as
    suppressed so it is excluded from every outreach surface. Limited companies
    are skipped (legal persons, out of Robinson scope).
    """
    from .compliance import LeadToScreen, RobinsonList, SupabaseScreeningWriter, run_robinson_screening
    from .config import settings
    from .db import get_client
    from .jobs import JobRun

    db = get_client()
    robinson = RobinsonList.load(settings.robinson_list_path)
    if robinson.is_empty:
        typer.secho(
            "WARNING: Robinson list is empty (ROBINSON_LIST_PATH unset or missing). "
            "Screening will suppress nothing — do not start live outreach until the "
            "register is provisioned.",
            fg=typer.colors.YELLOW,
            err=True,
        )

    res = (
        db.table("leads")
        .select("id,company_name,postal_code,is_sole_trader")
        .eq("is_sole_trader", True)
        .eq("suppressed", False)
        .limit(limit)
        .execute()
    )
    leads = [
        LeadToScreen(
            lead_id=row["id"],
            company_name=row["company_name"],
            postal_code=row.get("postal_code"),
            is_sole_trader=bool(row.get("is_sole_trader")),
        )
        for row in (res.data or [])
    ]

    with JobRun(db, "screen", payload={"limit": limit, "list_size": len(robinson)}) as job:
        stats = run_robinson_screening(leads, robinson, SupabaseScreeningWriter(db))
        job.result = stats.as_dict()

    typer.echo(json.dumps(stats.as_dict(), indent=2))


if __name__ == "__main__":
    app()

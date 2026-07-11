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
    from .jobs import JobRun
    from .pipeline import enrich_financial_leads

    db = get_client()
    with JobRun(db, "enrich-financial", payload={"limit": limit}) as job:
        stats = enrich_financial_leads(db, settings, limit=limit)
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
    from .jobs import JobRun
    from .pipeline import qualify_leads

    db = get_client()
    with JobRun(db, "qualify", payload={"limit": limit, "only_unknown": only_unknown}) as job:
        stats = qualify_leads(db, settings, limit=limit, only_unknown=only_unknown)
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
    from .config import settings
    from .db import get_client
    from .jobs import JobRun
    from .pipeline import score_leads

    db = get_client()
    with JobRun(db, "score", payload={"limit": limit, "only_qualified": only_qualified}) as job:
        stats = score_leads(db, settings, limit=limit, only_qualified=only_qualified)
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
    from .config import settings
    from .db import get_client
    from .jobs import JobRun
    from .pipeline import generate_angles

    db = get_client()
    with JobRun(db, "angles", payload={"limit": limit, "only_missing": only_missing}) as job:
        stats = generate_angles(db, settings, limit=limit, only_missing=only_missing)
        job.result = stats.as_dict()

    typer.echo(json.dumps(stats.as_dict(), indent=2))


@app.command(name="find-phones")
def find_phones_cmd(
    limit: int = typer.Option(500, help="Max phone-less leads to process in this run."),
) -> None:
    """Recover a phone number for leads that have none (website scrape → P-enhed).

    Phone-first outreach means a lead with no number is disqualified, so this
    runs as part of enrichment; use this command to backfill an existing book.
    """
    from .config import settings
    from .db import get_client
    from .jobs import JobRun
    from .pipeline import find_missing_phones

    db = get_client()
    with JobRun(db, "find-phones", payload={"limit": limit}) as job:
        result = find_missing_phones(db, settings, limit=limit)
        job.result = result

    typer.echo(json.dumps(result, indent=2))


@app.command(name="enrich-queued")
def enrich_queued_cmd(
    limit: int = typer.Option(200, help="Max queued leads per batch."),
    drain: bool = typer.Option(
        False, help="Loop until the queue is empty (the on-demand worker's mode)."
    ),
) -> None:
    """Enrich leads the user opted in (enrichment_status='queued').

    Runs the full pipeline — qualify → enrich-financial → score → angles —
    scoped to exactly the queued set, then flips them to 'enriched'. With
    --drain it loops until nothing is queued (used by the on-demand machine that
    the web app starts on opt-in); otherwise it does a single batch of `limit`.
    """
    from .config import settings
    from .db import get_client
    from .jobs import JobRun
    from .pipeline import drain_queued, enrich_queued

    db = get_client()
    with JobRun(db, "enrich-queued", payload={"limit": limit, "drain": drain}) as job:
        result = (
            drain_queued(db, settings, batch=limit)
            if drain
            else enrich_queued(db, settings, limit=limit)
        )
        job.result = result

    typer.echo(json.dumps(result, indent=2))


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

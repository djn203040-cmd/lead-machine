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


if __name__ == "__main__":
    app()

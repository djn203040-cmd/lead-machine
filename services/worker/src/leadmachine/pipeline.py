"""Enrichment pipeline orchestration.

Each stage runner below encapsulates one thing: select the leads to process
(optionally restricted to an explicit id set), map rows to the stage's models,
run the stage, and return its stats. The CLI commands and the ``enrich-queued``
orchestrator both call these runners, so the select/map logic lives in exactly
one place (no drift between "run a stage by hand" and "run the queue").

``enrich_queued`` is the web app's counterpart: discovery marks a lead
``enrichment_status='queued'`` when the user opts in; this walks the queued set
through qualify → financial → score → angles and flips it to ``enriched``.
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from .config import Settings

# Flip lead statuses in bounded batches (PostgREST caps request URL length).
_STATUS_CHUNK = 200


def _one(value: Any) -> Any:
    return (value[0] if value else None) if isinstance(value, list) else value


def _scope(query: Any, lead_ids: list[str] | None) -> Any:
    """Restrict a stage query to an explicit lead-id set, if given."""
    return query.in_("id", lead_ids) if lead_ids is not None else query


def set_enrichment_status(db: Client, lead_ids: list[str], status: str) -> None:
    """Set ``enrichment_status`` on the given leads (chunked)."""
    for i in range(0, len(lead_ids), _STATUS_CHUNK):
        chunk = lead_ids[i : i + _STATUS_CHUNK]
        db.table("leads").update({"enrichment_status": status}).in_("id", chunk).execute()


def queued_lead_ids(db: Client, limit: int) -> list[str]:
    """Lead ids awaiting enrichment, oldest first."""
    res = (
        db.table("leads")
        .select("id")
        .eq("enrichment_status", "queued")
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return [r["id"] for r in (res.data or [])]


def qualify_leads(
    db: Client,
    settings: Settings,
    *,
    limit: int,
    only_unknown: bool = True,
    lead_ids: list[str] | None = None,
) -> Any:
    from .website import (
        ClaudeGrader,
        DnsResolver,
        HttpxFetcher,
        PageSpeedClient,
        SupabaseWebsiteWriter,
        WebsiteDeps,
        WebsiteDiscoverer,
        run_qualification,
    )
    from .cvr.penhed import current_pnummer
    from .website.models import LeadToQualify

    query = db.table("leads").select(
        "id,website,company_name,email,phone,city,postal_code,cvr_number,address,"
        "lead_enrichment(cvr)"
    ).not_.is_("cvr_number", "null")
    if only_unknown:
        query = query.eq("website_need", "unknown")
    res = _scope(query, lead_ids).limit(limit).execute()
    leads = [
        LeadToQualify(
            lead_id=r["id"],
            website=r.get("website"),
            company_name=r.get("company_name"),
            email=r.get("email"),
            phone=list(r.get("phone") or []),
            city=r.get("city"),
            postal_code=r.get("postal_code"),
            cvr_number=r.get("cvr_number"),
            address=r.get("address"),
            pnummer=current_pnummer((_one(r.get("lead_enrichment")) or {}).get("cvr")),
        )
        for r in (res.data or [])
    ]

    psi = PageSpeedClient.from_settings(settings) if settings.pagespeed_api_key else None
    fetcher = HttpxFetcher()
    resolver = DnsResolver()
    # Discovery (email domain → name guess → Brave) always runs; Brave is only
    # wired in when its key is set. Grading is on when an Anthropic key is set.
    discoverer = WebsiteDiscoverer.from_settings(settings, fetcher, resolver)
    grader = ClaudeGrader.from_settings(settings) if settings.anthropic_api_key else None
    try:
        deps = WebsiteDeps(
            fetcher=fetcher,
            resolver=resolver,
            pagespeed=psi,
            discoverer=discoverer,
            grader=grader,
        )
        return run_qualification(leads, deps, SupabaseWebsiteWriter(db))
    finally:
        fetcher.close()
        discoverer.close()
        if psi is not None:
            psi.close()
        if grader is not None:
            grader.close()


def enrich_financial_leads(
    db: Client,
    settings: Settings,
    *,
    limit: int,
    lead_ids: list[str] | None = None,
) -> Any:
    from .financial import FinancialClient, SupabaseFinancialWriter, run_financial_enrichment
    from .financial.models import LeadToEnrich

    query = (
        db.table("leads")
        .select("id,cvr_number,branchekode,employees_exact,employees_band,lead_enrichment(cvr)")
        .not_.is_("cvr_number", "null")
    )
    res = _scope(query, lead_ids).limit(limit).execute()

    leads = []
    for row in res.data or []:
        enr = _one(row.get("lead_enrichment"))
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

    with FinancialClient.from_settings(settings) as client:
        return run_financial_enrichment(leads, client, SupabaseFinancialWriter(db))


def score_leads(
    db: Client,
    settings: Settings,
    *,
    limit: int,
    only_qualified: bool = True,
    lead_ids: list[str] | None = None,
) -> Any:
    from .scoring import LeadToScore, SupabaseScoreWriter, Weights, run_scoring

    criteria = db.table("scoring_criteria").select("key,weight,config,is_active").execute()
    weights = Weights.from_criteria(criteria.data or [])

    query = db.table("leads").select(
        "id,website_need,branchekode,employees_band,employees_exact,founded_at,"
        "cvr_status,reklamebeskyttet,lead_enrichment(website,social,financial)"
    )
    if only_qualified:
        query = query.neq("website_need", "unknown")
    res = _scope(query, lead_ids).limit(limit).execute()

    leads = []
    for row in res.data or []:
        enr = _one(row.get("lead_enrichment")) or {}
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

    return run_scoring(leads, SupabaseScoreWriter(db), weights=weights)


def generate_angles(
    db: Client,
    settings: Settings,
    *,
    limit: int,
    only_missing: bool = True,
    lead_ids: list[str] | None = None,
) -> Any:
    from .angles import ClaudeAnglesClient, SupabaseAngleWriter, run_angles
    from .angles.models import LeadForAngle
    from .financial.estimate import band_midpoint

    query = (
        db.table("leads")
        .select(
            "id,company_name,city,branche_text,website_need,employees_band,employees_exact,"
            "score,lead_enrichment(website,social,financial),lead_scores(breakdown),"
            "lead_angles(lead_id)"
        )
        .neq("website_need", "unknown")
    )
    res = _scope(query, lead_ids).limit(limit).execute()

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

    with ClaudeAnglesClient.from_settings(settings) as client:
        return run_angles(leads, client, SupabaseAngleWriter(db))


def enrich_queued(db: Client, settings: Settings, *, limit: int = 200) -> dict[str, Any]:
    """Run the full enrichment pipeline over leads the user opted in.

    Selects ``enrichment_status='queued'`` leads, marks them ``enriching`` so a
    concurrent run won't double-process them, walks qualify → financial → score
    → angles scoped to exactly that set, then flips them to ``enriched``. On a
    stage error the batch is marked ``failed`` (safe to re-queue) and re-raised.
    """
    ids = queued_lead_ids(db, limit)
    if not ids:
        return {"queued": 0, "enriched": 0}

    set_enrichment_status(db, ids, "enriching")
    try:
        n = len(ids)
        qualify = qualify_leads(db, settings, limit=n, only_unknown=True, lead_ids=ids)
        financial = enrich_financial_leads(db, settings, limit=n, lead_ids=ids)
        scored = score_leads(db, settings, limit=n, only_qualified=True, lead_ids=ids)
        angles = generate_angles(db, settings, limit=n, only_missing=True, lead_ids=ids)
    except Exception:
        set_enrichment_status(db, ids, "failed")
        raise

    set_enrichment_status(db, ids, "enriched")
    return {
        "queued": len(ids),
        "enriched": len(ids),
        "qualify": qualify.as_dict(),
        "financial": financial.as_dict(),
        "score": scored.as_dict(),
        "angles": angles.as_dict(),
    }


def drain_queued(
    db: Client, settings: Settings, *, batch: int = 100, max_rounds: int = 50
) -> dict[str, Any]:
    """Drain the whole enrichment queue: run ``enrich_queued`` until it's empty.

    This is what the on-demand worker machine runs — the web app starts the
    machine on opt-in, it drains everything queued (including leads queued by
    other searches while it runs), then exits. ``max_rounds`` bounds a runaway
    loop; each round processes up to ``batch`` leads.
    """
    rounds = 0
    enriched = 0
    while rounds < max_rounds:
        res = enrich_queued(db, settings, limit=batch)
        if not res.get("queued"):
            break
        rounds += 1
        enriched += res.get("enriched", 0)
    return {"rounds": rounds, "enriched": enriched}

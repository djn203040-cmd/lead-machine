from leadmachine.financial.enrich import (
    SupabaseFinancialWriter,
    enrich_one,
    run_financial_enrichment,
)
from leadmachine.financial.models import LeadToEnrich, Report

from .conftest import FakeFinancialWriter, FakeSupabase, MockFinancialClient

REPORT = Report(
    cvr_number="12345678",
    period_start="2023-01-01",
    period_end="2023-12-31",
    published_at="2024-05-15T10:00:00+02:00",
    xbrl_url="https://regnskaber.virk.dk/rep-2023.xml",
)


def _lead(**kw) -> LeadToEnrich:
    base = dict(lead_id="L1", cvr_number="12345678", branchekode="960210")
    base.update(kw)
    return LeadToEnrich(**base)


def test_enrich_one_with_report_builds_financial_and_contact(xbrl_bytes, deltager_record) -> None:
    client = MockFinancialClient(REPORT, xbrl_bytes)
    lead = _lead(employees_band="ANTAL_2_4", raw_cvr=deltager_record)

    financial, contact = enrich_one(lead, client)

    assert financial["source"] == "virk_xbrl"
    assert financial["currency"] == "DKK"
    assert financial["period"] == {"start": "2023-01-01", "end": "2023-12-31"}
    assert financial["gross_profit"] == 1_200_000
    assert financial["equity"] == 900_000
    assert "revenue" not in financial  # actual revenue was omitted in the XBRL
    # 1_200_000 / 0.80 gross margin (beauty_wellness)
    assert financial["revenue_estimate"]["value"] == 1_500_000
    assert financial["revenue_estimate"]["method"] == "gross_margin_backout"

    assert contact == {"source": "cvr", "decision_makers": [{"name": "Jens Hansen", "role": "adm. dir."}]}


def test_enrich_one_without_report_estimates_from_employees() -> None:
    client = MockFinancialClient(None, None)
    lead = _lead(employees_exact=4, raw_cvr=None)

    financial, contact = enrich_one(lead, client)

    assert financial["source"] == "estimate_only"
    assert financial["revenue_estimate"]["method"] == "per_employee"
    assert financial["revenue_estimate"]["value"] == 4 * 500_000
    assert contact == {}


def test_enrich_one_empty_when_nothing_available() -> None:
    client = MockFinancialClient(None, None)
    lead = _lead(branchekode=None, employees_exact=None, employees_band=None, raw_cvr=None)
    assert enrich_one(lead, client) == ({}, {})


def test_run_financial_enrichment_tallies_and_persists(xbrl_bytes, deltager_record) -> None:
    client = MockFinancialClient(REPORT, xbrl_bytes)
    writer = FakeFinancialWriter()
    leads = [
        _lead(lead_id="A", raw_cvr=deltager_record),
        _lead(lead_id="B", raw_cvr=None),
    ]

    stats = run_financial_enrichment(leads, client, writer)

    assert stats.seen == 2
    assert stats.reports == 2
    assert stats.revenue == 2
    assert stats.contacts == 1  # only A had a CVR payload
    assert stats.empty == 0
    assert stats.errors == 0
    assert set(writer.writes) == {"A", "B"}


def test_supabase_financial_writer_upserts_enrichment() -> None:
    fake = FakeSupabase()
    SupabaseFinancialWriter(fake).write(
        "lead-1", {"source": "virk_xbrl", "gross_profit": 1}, {"source": "cvr"}
    )
    assert len(fake.log) == 1
    name, row, on_conflict = fake.log[0]
    assert (name, on_conflict) == ("lead_enrichment", "lead_id")
    assert row["lead_id"] == "lead-1"
    assert row["financial"]["gross_profit"] == 1
    assert row["contact"]["source"] == "cvr"
    assert "last_enriched_at" in row

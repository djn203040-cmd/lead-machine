from leadmachine.cvr.discovery import SupabaseLeadWriter, run_discovery
from leadmachine.cvr.query import SearchParameters

from .conftest import FakeSupabase, MockCvrClient


def test_run_discovery_suppresses_and_dedups(companies, fake_writer) -> None:
    client = MockCvrClient(companies)
    stats = run_discovery(client, SearchParameters(), fake_writer, search_id="search-1")

    assert stats.seen == 4
    assert stats.suppressed_reklame == 1  # the reklamebeskyttet restaurant
    assert stats.suppressed_inactive == 1  # the bankrupt sole-trader
    assert stats.upserted == 2  # active hairdresser appears twice (same CVR)
    assert stats.errors == 0

    # dedup: the duplicate CVR collapses to a single stored lead
    assert fake_writer.count == 1
    assert "12345678" in fake_writer.store
    lead, raw, search_id = fake_writer.store["12345678"]
    assert search_id == "search-1"
    assert raw["cvrNummer"] == 12345678


def test_search_params_passed_through(companies, fake_writer) -> None:
    client = MockCvrClient(companies)
    params = SearchParameters(branchekoder=["960210"])
    run_discovery(client, params, fake_writer)
    assert client.last_params is params


def test_mapping_errors_are_counted_not_fatal(fake_writer) -> None:
    bad = {"virksomhedMetadata": {}}  # no cvrNummer -> map_company raises
    good = {"cvrNummer": 11111111, "virksomhedMetadata": {"nyesteNavn": {"navn": "OK"},
            "sammensatStatus": "NORMAL"}}
    client = MockCvrClient([bad, good])
    stats = run_discovery(client, SearchParameters(), fake_writer)
    assert stats.seen == 2
    assert stats.errors == 1
    assert stats.upserted == 1


def test_stats_as_dict() -> None:
    from leadmachine.cvr.discovery import DiscoveryStats

    d = DiscoveryStats(seen=3, upserted=2).as_dict()
    assert d == {"seen": 3, "upserted": 2, "suppressed_reklame": 0,
                 "suppressed_inactive": 0, "errors": 0}


def test_supabase_writer_upserts_lead_then_enrichment(companies) -> None:
    fake = FakeSupabase()
    writer = SupabaseLeadWriter(fake)
    from leadmachine.cvr.mapper import map_company

    lead = map_company(companies[0])
    writer.upsert(lead, companies[0], "search-9")

    assert len(fake.log) == 2
    (t1, row1, oc1), (t2, row2, oc2) = fake.log
    assert (t1, oc1) == ("leads", "cvr_number")
    assert row1["cvr_number"] == "12345678"
    assert row1["search_id"] == "search-9"
    assert (t2, oc2) == ("lead_enrichment", "lead_id")
    assert row2["lead_id"] == "lead-uuid-1"
    assert row2["cvr"]["cvrNummer"] == 12345678
    assert "last_enriched_at" in row2

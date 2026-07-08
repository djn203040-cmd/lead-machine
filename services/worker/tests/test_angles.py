"""Tests for AI Danish sales-angle generation (M6) — no network, no API key."""

from __future__ import annotations

import pytest

from leadmachine.angles import (
    Angle,
    LeadForAngle,
    SupabaseAngleWriter,
    build_prompt,
    build_user_prompt,
    generate_one,
    run_angles,
)
from leadmachine.angles.client import ANGLE_SCHEMA
from leadmachine.angles.prompt import SYSTEM_PROMPT

from .conftest import FakeAngleWriter, FakeSupabase, MockAnglesClient


def _lead(**kw) -> LeadForAngle:
    base = dict(lead_id="L1", company_name="Salon Sax", website_need="none")
    base.update(kw)
    return LeadForAngle(**base)


# --- prompt building -------------------------------------------------------
def test_build_user_prompt_includes_core_facts() -> None:
    lead = _lead(
        branche_text="Frisørsaloner",
        city="Aarhus",
        employees=3,
        score=87,
        website_need="none",
    )
    prompt = build_user_prompt(lead)
    assert "Salon Sax" in prompt
    assert "Frisørsaloner" in prompt
    assert "Aarhus" in prompt
    assert "Antal ansatte: 3" in prompt
    assert "87" in prompt
    assert "Ingen hjemmeside" in prompt


def test_build_user_prompt_derives_weaknesses_from_signals() -> None:
    lead = _lead(
        website_need="bad",
        website={
            "signals": {
                "has_viewport": False,
                "has_https": False,
                "legacy_markup": True,
                "copyright_year": 2009,
                "is_one_page": True,
            },
            "pagespeed": {"performance": 35},
        },
    )
    prompt = build_user_prompt(lead)
    assert "ikke mobilvenlig" in prompt
    assert "ingen HTTPS" in prompt.lower() or "ingen https" in prompt.lower()
    assert "2009" in prompt
    assert "langsom på mobil" in prompt


def test_build_user_prompt_includes_revenue_social_and_factors() -> None:
    lead = _lead(
        financial={"revenue_estimate": {"value": 1_500_000, "confidence": "medium"}},
        social={"has_fb_page": True, "has_meta_pixel": True},
        score_breakdown={
            "factors": {
                "website_need": {"points": 45, "max": 45},
                "budget": {"points": 14, "max": 20},
            }
        },
    )
    prompt = build_user_prompt(lead)
    assert "1.500.000 DKK" in prompt
    assert "medium" in prompt
    assert "Facebook-side" in prompt
    assert "Meta Pixel" in prompt
    assert "Hjemmesidebehov 45/45" in prompt


def test_build_prompt_returns_system_and_user() -> None:
    system, user = build_prompt(_lead())
    assert system == SYSTEM_PROMPT
    assert "Salon Sax" in user


# --- Angle parsing ---------------------------------------------------------
def test_angle_from_payload_maps_fields() -> None:
    angle = Angle.from_payload(
        {
            "summary_da": "  Resumé  ",
            "weaknesses_da": "Svagheder",
            "angle_da": "Vinkel",
            "opening_line_da": "Hej!",
            "competitor_name": "Klip & Co",
            "competitor_angle_type": "fomo",
        }
    )
    assert angle.summary_da == "Resumé"  # trimmed
    assert angle.competitor_name == "Klip & Co"
    assert angle.competitor_angle_type == "fomo"


def test_angle_from_payload_parses_cta_and_objections() -> None:
    angle = Angle.from_payload(
        {
            "summary_da": "x",
            "weaknesses_da": "y",
            "angle_da": "z",
            "opening_line_da": "w",
            "cta_da": "  Skal vi tage et kort kald?  ",
            "objections": [
                {"objection_da": "  Send mig en mail  ", "response_da": "  Klart  "},
                {"objection_da": "", "response_da": "dropped — no objection"},
                "not a dict — ignored",
                {"objection_da": "Hvad koster det?", "response_da": "Gratis at se."},
                {"objection_da": "En for meget", "response_da": "kappes ved 3"},
            ],
            "competitor_name": "",
            "competitor_angle_type": "none",
        }
    )
    assert angle.cta_da == "Skal vi tage et kort kald?"  # trimmed
    # malformed/blank items dropped, list capped at 3
    assert angle.objections == [
        {"objection_da": "Send mig en mail", "response_da": "Klart"},
        {"objection_da": "Hvad koster det?", "response_da": "Gratis at se."},
        {"objection_da": "En for meget", "response_da": "kappes ved 3"},
    ]


def test_angle_from_payload_defaults_missing_cta_and_objections() -> None:
    angle = Angle.from_payload(
        {
            "summary_da": "x",
            "weaknesses_da": "y",
            "angle_da": "z",
            "opening_line_da": "w",
            "competitor_name": "",
            "competitor_angle_type": "none",
        }
    )
    assert angle.cta_da == ""
    assert angle.objections == []


def test_angle_as_row_carries_cta_and_objections() -> None:
    row = Angle(
        summary_da="s",
        weaknesses_da="w",
        angle_da="a",
        opening_line_da="o",
        cta_da="c",
        objections=[{"objection_da": "q", "response_da": "r"}],
    ).as_row()
    assert row["cta_da"] == "c"
    assert row["objections"] == [{"objection_da": "q", "response_da": "r"}]


def test_angle_from_payload_coerces_invalid_category_and_blank_name() -> None:
    angle = Angle.from_payload(
        {
            "summary_da": "x",
            "weaknesses_da": "y",
            "angle_da": "z",
            "opening_line_da": "w",
            "competitor_name": "   ",
            "competitor_angle_type": "bogus",
        }
    )
    assert angle.competitor_angle_type == "none"
    assert angle.competitor_name is None


def test_angle_none_category_drops_competitor_name() -> None:
    angle = Angle.from_payload(
        {
            "summary_da": "x",
            "weaknesses_da": "y",
            "angle_da": "z",
            "opening_line_da": "w",
            "competitor_name": "Some Name",
            "competitor_angle_type": "none",
        }
    )
    assert angle.competitor_name is None


def test_angle_as_row_empties_to_null() -> None:
    row = Angle(
        summary_da="s", weaknesses_da="", angle_da="a", opening_line_da="o"
    ).as_row()
    assert row["summary_da"] == "s"
    assert row["weaknesses_da"] is None
    assert row["competitor_angle_type"] == "none"
    assert row["competitor_name"] is None


# --- schema sanity ---------------------------------------------------------
def test_angle_schema_is_strict_and_complete() -> None:
    assert ANGLE_SCHEMA["additionalProperties"] is False
    assert set(ANGLE_SCHEMA["required"]) == set(ANGLE_SCHEMA["properties"])
    assert ANGLE_SCHEMA["properties"]["competitor_angle_type"]["enum"] == [
        "fomo",
        "first_mover",
        "none",
    ]


# --- generate_one + run_angles --------------------------------------------
def test_generate_one_calls_client_and_parses() -> None:
    client = MockAnglesClient()
    angle = generate_one(_lead(), client)
    assert angle.competitor_angle_type == "first_mover"
    assert angle.opening_line_da.startswith("Hej")
    assert len(client.calls) == 1
    assert "Salon Sax" in client.calls[0][1]  # the user prompt


def test_run_angles_tallies_skips_and_persists() -> None:
    client = MockAnglesClient()
    writer = FakeAngleWriter()
    leads = [
        _lead(lead_id="A", website_need="none"),
        _lead(lead_id="B", website_need="bad"),
        _lead(lead_id="C", website_need="unknown"),  # not qualified → skipped
    ]
    stats = run_angles(leads, client, writer)

    assert stats.seen == 3
    assert stats.generated == 2
    assert stats.skipped == 1
    assert stats.errors == 0
    assert set(writer.writes) == {"A", "B"}
    assert writer.writes["A"]["competitor_angle_type"] == "first_mover"


def test_run_angles_counts_client_errors() -> None:
    class BoomClient:
        def generate(self, system: str, user: str):
            raise RuntimeError("api down")

    stats = run_angles([_lead()], BoomClient(), FakeAngleWriter())
    assert stats.errors == 1
    assert stats.generated == 0


def test_supabase_angle_writer_upserts_lead_angles() -> None:
    fake = FakeSupabase()
    angle = Angle(
        summary_da="s",
        weaknesses_da="w",
        angle_da="a",
        opening_line_da="o",
        competitor_angle_type="none",
    )
    SupabaseAngleWriter(fake).write("lead-1", angle.as_row())

    assert len(fake.log) == 1
    name, row, on_conflict = fake.log[0]
    assert (name, on_conflict) == ("lead_angles", "lead_id")
    assert row["lead_id"] == "lead-1"
    assert row["summary_da"] == "s"
    assert "generated_at" in row


@pytest.mark.parametrize("need", ["none", "dead", "parked", "facebook_only"])
def test_no_site_weakness_is_single_clear_line(need: str) -> None:
    prompt = build_user_prompt(_lead(website_need=need))
    # exactly one bullet for the "no usable site" buckets
    assert prompt.count("\n- ") == 1

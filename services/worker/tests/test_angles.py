"""Tests for AI Danish sales-angle generation (M6, savings angle v3).

No network, no API key.
"""

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


def test_build_user_prompt_leads_with_the_savings_math() -> None:
    lead = _lead(
        branchekode="962100",  # frisør → beauty_wellness, 12%
        financial={"revenue_estimate": {"value": 2_000_000, "confidence": "medium"}},
    )
    prompt = build_user_prompt(lead)
    assert "BESPARELSESPOTENTIALE" in prompt
    assert "Realistisk årlig besparelse" in prompt
    assert "240.000" in prompt  # 12% of 2M, the top of the band
    assert "Jeres honorar (20%" in prompt
    assert "Virksomheden beholder" in prompt
    # The number is an estimate from public data — never sold as a promise.
    assert "aldrig" in prompt and "løfte" in prompt


def test_unknown_headcount_is_flagged_next_to_the_number() -> None:
    """Nothing bounds the estimate when we don't know how many hands there are."""
    money = {"revenue_estimate": {"value": 9_000_000, "confidence": "medium"}}
    unknown = build_user_prompt(_lead(branchekode="962100", employees=None, financial=money))
    known = build_user_prompt(_lead(branchekode="962100", employees=4, financial=money))
    assert "antal ansatte er ukendt" in unknown
    # With a headcount the estimate is bounded, so the warning is unnecessary.
    assert "antal ansatte er ukendt" not in known


def test_build_user_prompt_forbids_figures_without_a_revenue_signal() -> None:
    prompt = build_user_prompt(_lead(financial={}))
    assert "Intet omsætningsestimat" in prompt
    assert "IKKE konkrete kronebeløb" in prompt
    assert "Realistisk årlig besparelse" not in prompt


def test_build_user_prompt_lists_sector_time_sinks() -> None:
    salon = build_user_prompt(_lead(branchekode="962100"))
    builder = build_user_prompt(_lead(branchekode="433900"))
    assert "TIDSRØVERE" in salon
    assert "hypoteser" in salon  # ask, don't assert
    assert salon != builder


def test_website_status_is_background_not_the_pitch() -> None:
    prompt = build_user_prompt(_lead(website_need="none"))
    assert "TEKNISK MODENHED" in prompt
    assert "må ikke bruges som salgsvinkel" in prompt
    assert "Ingen hjemmeside" in prompt
    assert "lav digital modenhed" in prompt


def test_modern_site_reads_as_an_easy_systems_conversation() -> None:
    prompt = build_user_prompt(_lead(website_need="modern"))
    assert "digitalt med" in prompt


def test_build_user_prompt_includes_revenue_social_and_factors() -> None:
    lead = _lead(
        financial={"revenue_estimate": {"value": 1_500_000, "confidence": "medium"}},
        social={"has_fb_page": True, "has_meta_pixel": True},
        score_breakdown={
            "factors": {
                "savings": {"points": 34, "max": 40},
                "industry": {"points": 20, "max": 20},
            }
        },
    )
    prompt = build_user_prompt(lead)
    assert "1.500.000 DKK" in prompt
    assert "medium" in prompt
    assert "Facebook-side" in prompt
    assert "Meta Pixel" in prompt
    assert "Besparelsespotentiale 34/40" in prompt


def test_build_user_prompt_includes_phone_type() -> None:
    assert "Mobilnummer" in build_user_prompt(_lead(phone_type="mobile"))
    landline = build_user_prompt(_lead(phone_type="landline"))
    assert "hovednummer" in landline and "gatekeeper" in landline
    assert "omstilling" in build_user_prompt(_lead(phone_type="service"))
    # Unknown/missing type → no line, and the model defaults to owner-direct.
    assert "Telefonnummer-type" not in build_user_prompt(_lead(phone_type=None))


def test_system_prompt_sells_savings_not_websites() -> None:
    assert "20%" in SYSTEM_PROMPT
    assert "NOT A WEBSITE PITCH" in SYSTEM_PROMPT
    assert "does NOT sell websites" in SYSTEM_PROMPT
    assert "NEVER promise a specific saving" in SYSTEM_PROMPT


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


def test_run_angles_pitches_leads_with_an_unqualified_website() -> None:
    """The savings pitch doesn't need a website verdict — don't skip those."""
    client = MockAnglesClient()
    writer = FakeAngleWriter()
    leads = [
        _lead(lead_id="A", website_need="none"),
        _lead(lead_id="B", website_need="bad"),
        _lead(lead_id="C", website_need="unknown"),
    ]
    stats = run_angles(leads, client, writer)

    assert stats.seen == 3
    assert stats.generated == 3
    assert stats.skipped == 0
    assert stats.errors == 0
    assert set(writer.writes) == {"A", "B", "C"}
    assert writer.writes["A"]["competitor_angle_type"] == "first_mover"


def test_run_angles_can_still_opt_into_skipping_unqualified() -> None:
    stats = run_angles(
        [_lead(lead_id="C", website_need="unknown")],
        MockAnglesClient(),
        FakeAngleWriter(),
        skip_unqualified=True,
    )
    assert stats.skipped == 1
    assert stats.generated == 0


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


@pytest.mark.parametrize("need", ["none", "dead", "parked", "facebook_only", "modern"])
def test_every_website_state_still_produces_a_usable_brief(need: str) -> None:
    """Website state can't gate the pitch any more — every bucket must brief."""
    prompt = build_user_prompt(_lead(website_need=need, branchekode="962100"))
    assert "TIDSRØVERE" in prompt
    assert "Læsning:" in prompt

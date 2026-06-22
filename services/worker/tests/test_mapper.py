import pytest

from leadmachine.cvr.mapper import (
    SUPPRESS_INACTIVE,
    SUPPRESS_REKLAME,
    map_company,
)


def test_maps_active_company_fields(companies) -> None:
    lead = map_company(companies[0])
    assert lead.cvr_number == "12345678"
    assert lead.company_name == "Salon Klip ApS"
    assert lead.address == "Nørrebrogade 12A, 1 tv"
    assert lead.postal_code == "2200"
    assert lead.city == "København N"
    assert lead.kommune == "København"
    assert lead.email == "kontakt@salonklip.dk"
    assert lead.website == "https://www.facebook.com/salonklip"
    assert lead.branchekode == "960210"
    assert lead.branche_text == "Frisørsaloner"
    assert lead.company_form == "Anpartsselskab"
    assert lead.cvr_status == "NORMAL"
    assert lead.employees_band == "ANTAL_2_4"
    assert lead.employees_exact == 3
    assert lead.founded_at == "2018-01-15"
    assert lead.reklamebeskyttet is False
    assert lead.is_sole_trader is False


def test_phone_excludes_secret_and_expired(companies) -> None:
    # only the current, non-secret number survives
    lead = map_company(companies[0])
    assert lead.phone == ["12345678"]


def test_active_company_is_not_suppressed(companies) -> None:
    lead = map_company(companies[0])
    assert lead.is_active is True
    assert lead.suppression_reason is None


def test_reklamebeskyttet_is_suppressed(companies) -> None:
    lead = map_company(companies[1])
    assert lead.reklamebeskyttet is True
    assert lead.suppression_reason == SUPPRESS_REKLAME


def test_bankrupt_sole_trader_is_suppressed(companies) -> None:
    lead = map_company(companies[2])
    assert lead.cvr_status == "OPLØST EFTER KONKURS"
    assert lead.is_active is False
    assert lead.suppression_reason == SUPPRESS_INACTIVE
    assert lead.is_sole_trader is True


def test_accepts_wrapped_source(sources) -> None:
    # the raw _source ({"Vrvirksomhed": {...}}) maps the same as the unwrapped form
    lead = map_company(sources[0])
    assert lead.cvr_number == "12345678"


def test_missing_cvr_number_raises() -> None:
    with pytest.raises(ValueError):
        map_company({"Vrvirksomhed": {"virksomhedMetadata": {}}})


def test_to_lead_row_has_expected_columns(companies) -> None:
    row = map_company(companies[0]).to_lead_row()
    for col in ("cvr_number", "company_name", "phone", "reklamebeskyttet", "is_sole_trader"):
        assert col in row
    assert isinstance(row["phone"], list)

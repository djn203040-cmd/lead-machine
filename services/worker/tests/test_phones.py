"""Tests for Danish phone-number extraction from a business's own page."""

from __future__ import annotations

from leadmachine.website.phones import (
    best_phone_type,
    classify_phone,
    extract_phones,
    normalize_phone,
)


# --- normalize_phone -------------------------------------------------------
def test_normalize_strips_spaces_and_country_code() -> None:
    assert normalize_phone("32 34 56 78") == "32345678"
    assert normalize_phone("+45 23 45 67 89") == "23456789"
    assert normalize_phone("0045 33445566") == "33445566"


def test_normalize_rejects_non_danish() -> None:
    assert normalize_phone("3234567") is None  # too short
    assert normalize_phone("323456789") is None  # too long (not +45)
    assert normalize_phone("32345678") == "32345678"
    assert normalize_phone("00000000") is None  # first digit not 2-9
    assert normalize_phone("11223344") is None  # starts with 1
    assert normalize_phone(None) is None


# --- classify_phone / best_phone_type --------------------------------------
def test_classify_mobile_ranges() -> None:
    for n in ("20123456", "29999999", "30112233", "42112233", "53112233",
              "61112233", "71112233", "81112233", "93112233"):
        assert classify_phone(n) == "mobile", n


def test_classify_landline_ranges() -> None:
    for n in ("32345678", "45678901", "58112233", "65112233", "75112233",
              "86112233", "97112233"):
        assert classify_phone(n) == "landline", n


def test_classify_service_ranges() -> None:
    assert classify_phone("70112233") == "service"
    assert classify_phone("80112233") == "service"
    assert classify_phone("90112233") == "service"


def test_classify_normalizes_first() -> None:
    assert classify_phone("+45 20 12 34 56") == "mobile"
    assert classify_phone("0045 70112233") == "service"
    assert classify_phone("ikke et nummer") is None
    assert classify_phone(None) is None


def test_best_phone_type_prefers_most_personal() -> None:
    assert best_phone_type(["70112233", "86112233", "20123456"]) == "mobile"
    assert best_phone_type(["70112233", "86112233"]) == "landline"
    assert best_phone_type(["70112233"]) == "service"
    assert best_phone_type(["garbage"]) is None
    assert best_phone_type([]) is None
    assert best_phone_type(None) is None


# --- extract_phones --------------------------------------------------------
def test_extract_from_tel_href() -> None:
    html = '<a href="tel:+4523456789">Ring til os</a>'
    assert extract_phones(html) == ["23456789"]


def test_extract_from_plus45_and_cue() -> None:
    assert extract_phones("Kontakt os på +45 33 44 55 66 i dag") == ["33445566"]
    assert extract_phones("Tlf: 44 55 66 77") == ["44556677"]
    assert extract_phones("Telefon 45678901") == ["45678901"]


def test_bare_number_without_context_ignored() -> None:
    # No tel:/+45/cue — could be a CVR number, price, etc. Not trusted.
    assert extract_phones("CVR 45678901 · Bagergade 22") == []


def test_excludes_cvr_number() -> None:
    # The CVR number appears in a phone-like context but is excluded explicitly.
    html = "Tlf 45678901 · CVR 45678901"
    assert extract_phones(html, exclude=("45678901",)) == []


def test_dedupes_across_sources() -> None:
    html = '<a href="tel:23456789">Ring</a> eller tlf. 23 45 67 89'
    assert extract_phones(html) == ["23456789"]


def test_multiple_numbers_ordered_tel_first() -> None:
    html = 'Tlf 33445566. <a href="tel:22334455">mobil</a>'
    assert extract_phones(html) == ["22334455", "33445566"]


def test_empty_and_none() -> None:
    assert extract_phones("") == []
    assert extract_phones(None) == []

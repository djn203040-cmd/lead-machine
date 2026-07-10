"""Tests for production-unit (P-enhed) lookup + mapping."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx

from leadmachine.cvr.penhed import (
    EsPenhedClient,
    current_pnummer,
    map_penhed,
)

PENHED_SOURCE = {
    "Vrproduktionsenhed": {
        "pNummer": 1024698951,
        "navne": [
            {"navn": "Noribar", "periode": {"gyldigFra": "2019-05-13", "gyldigTil": None}}
        ],
        "telefonNummer": [
            {"kontaktoplysning": "71749999", "hemmelig": False, "periode": {"gyldigTil": None}}
        ],
        "elektroniskPost": [
            {"kontaktoplysning": "hej@noribar.dk", "hemmelig": False, "periode": {"gyldigTil": None}}
        ],
        "hjemmeside": [
            {"kontaktoplysning": "www.noribar.dk", "hemmelig": False, "periode": {"gyldigTil": None}}
        ],
        "produktionsEnhedMetadata": {
            "nyesteNavn": {"navn": "Noribar"},
            "nyesteBeliggenhedsadresse": {
                "vejnavn": "Skt. Clemens Stræde",
                "husnummerFra": 7,
                "postnummer": 8000,
                "postdistrikt": "Aarhus C",
            },
            "nyesteHovedbranche": {"branchekode": "561110"},
        },
    }
}


# --- current_pnummer -------------------------------------------------------
def test_current_pnummer_picks_open_period() -> None:
    blob = {
        "penheder": [
            {"pNummer": 111, "periode": {"gyldigTil": "2018-01-01"}},
            {"pNummer": 1024698951, "periode": {"gyldigTil": None}},
        ]
    }
    assert current_pnummer(blob) == "1024698951"


def test_current_pnummer_unwraps_vrvirksomhed() -> None:
    blob = {"Vrvirksomhed": {"penheder": [{"pNummer": 42, "periode": {"gyldigTil": None}}]}}
    assert current_pnummer(blob) == "42"


def test_current_pnummer_absent() -> None:
    assert current_pnummer(None) is None
    assert current_pnummer({}) is None
    assert current_pnummer({"penheder": []}) is None


# --- map_penhed ------------------------------------------------------------
def test_map_penhed_flattens_trading_name_and_contact() -> None:
    info = map_penhed(PENHED_SOURCE)
    assert info.pnummer == "1024698951"
    assert info.name == "Noribar"
    assert info.website == "www.noribar.dk"
    assert info.email == "hej@noribar.dk"
    assert info.phone == ["71749999"]
    assert info.address == "Skt. Clemens Stræde 7"
    assert info.postal_code == "8000"
    assert info.city == "Aarhus C"
    assert info.branchekode == "561110"


def test_map_penhed_name_falls_back_to_navne() -> None:
    rec = {"Vrproduktionsenhed": {"pNummer": 9, "navne": [{"navn": "Fallback Café"}]}}
    assert map_penhed(rec).name == "Fallback Café"


def test_map_penhed_secret_contact_skipped() -> None:
    rec = {
        "Vrproduktionsenhed": {
            "pNummer": 9,
            "hjemmeside": [{"kontaktoplysning": "secret.dk", "hemmelig": True, "periode": {"gyldigTil": None}}],
        }
    }
    assert map_penhed(rec).website is None


# --- EsPenhedClient --------------------------------------------------------
def _client(handler: httpx.MockTransport) -> EsPenhedClient:
    return EsPenhedClient(
        url="http://distribution.virk.dk/cvr-permanent/produktionsenhed/_search",
        http_client=httpx.Client(transport=handler),
    )


def test_fetch_by_pnummer_queries_term_and_maps() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"hits": {"hits": [{"_source": PENHED_SOURCE}]}})

    info = _client(httpx.MockTransport(handler)).fetch_by_pnummer("1024698951")
    assert info is not None
    assert info.name == "Noribar"
    body = json.loads(captured[0].content)
    assert body == {"size": 1, "query": {"term": {"Vrproduktionsenhed.pNummer": 1024698951}}}


def test_fetch_by_pnummer_no_hits_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"hits": {"hits": []}})

    assert _client(httpx.MockTransport(handler)).fetch_by_pnummer(1) is None


def test_fetch_by_pnummer_swallows_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    assert _client(httpx.MockTransport(handler)).fetch_by_pnummer(1) is None


def test_from_settings_requires_creds() -> None:
    assert EsPenhedClient.from_settings(SimpleNamespace(cvr_es_user="", cvr_es_password="")) is None
    got = EsPenhedClient.from_settings(
        SimpleNamespace(
            cvr_es_user="u",
            cvr_es_password="p",
            cvr_es_penhed_url="http://x/produktionsenhed/_search",
        )
    )
    assert isinstance(got, EsPenhedClient)
    got.close()

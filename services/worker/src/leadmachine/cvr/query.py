"""Search query builder (issue #16).

Translates a saved ``searches.parameters`` definition into a CVR Elasticsearch
query over the company index. Filters: branchekode(s), postnummer (discrete or
ranges), kommunekode(s), employee interval band, and company status.

The query is a single ``bool.filter`` so it stays a non-scoring, cacheable
filter context — the order of results is irrelevant for bulk discovery.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .branchekoder import normalize_code

# Default statuses we consider "active" — everything else is discovery-suppressed.
ACTIVE_STATUSES: tuple[str, ...] = ("NORMAL", "AKTIV")

# Valid employee interval-band codes (CVR ``intervalKodeAntalAnsatte``).
EMPLOYEE_BANDS: tuple[str, ...] = (
    "ANTAL_0_0",
    "ANTAL_1_1",
    "ANTAL_2_4",
    "ANTAL_5_9",
    "ANTAL_10_19",
    "ANTAL_20_49",
    "ANTAL_50_99",
    "ANTAL_100_199",
    "ANTAL_200_499",
    "ANTAL_500_999",
    "ANTAL_1000_999999",
)

# Elasticsearch field paths in the cvr-permanent company index.
_META = "Vrvirksomhed.virksomhedMetadata"
PATH_BRANCHEKODE = f"{_META}.nyesteHovedbranche.branchekode"
PATH_POSTNUMMER = f"{_META}.nyesteBeliggenhedsadresse.postnummer"
PATH_KOMMUNEKODE = f"{_META}.nyesteBeliggenhedsadresse.kommune.kommuneKode"
PATH_STATUS = f"{_META}.sammensatStatus"
# Employee band is published over three cadences; match any of them so we don't
# over-exclude small firms that only have a yearly figure.
PATHS_EMPLOYEE_BAND = (
    f"{_META}.nyesteMaanedsbeskaeftigelse.intervalKodeAntalAnsatte",
    f"{_META}.nyesteKvartalsbeskaeftigelse.intervalKodeAntalAnsatte",
    f"{_META}.nyesteAarsbeskaeftigelse.intervalKodeAntalAnsatte",
)


class SearchParameters(BaseModel):
    """The filter set stored in ``searches.parameters`` (jsonb)."""

    branchekoder: list[str] = Field(default_factory=list)
    postnumre: list[int] = Field(default_factory=list)
    # Inclusive [from, to] postal-code ranges, e.g. [[1000, 2999]] for Copenhagen.
    postnummer_ranges: list[list[int]] = Field(default_factory=list)
    kommunekoder: list[int] = Field(default_factory=list)
    employee_bands: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=lambda: list(ACTIVE_STATUSES))

    @field_validator("branchekoder")
    @classmethod
    def _normalize_branchekoder(cls, v: list[str]) -> list[str]:
        return [normalize_code(str(c)) for c in v]

    @field_validator("statuses")
    @classmethod
    def _upper_statuses(cls, v: list[str]) -> list[str]:
        # An explicit empty list disables the status filter; a missing value
        # falls back to ACTIVE_STATUSES via the field's default_factory.
        return [s.strip().upper() for s in v]

    @field_validator("postnummer_ranges")
    @classmethod
    def _check_ranges(cls, v: list[list[int]]) -> list[list[int]]:
        for r in v:
            if len(r) != 2:
                raise ValueError(f"postnummer_ranges entries must be [from, to], got {r!r}")
        return v


def _geo_clause(params: SearchParameters) -> dict[str, Any] | None:
    """Combine postnumre, postal ranges, and kommunekoder into one OR clause."""
    should: list[dict[str, Any]] = []
    if params.postnumre:
        should.append({"terms": {PATH_POSTNUMMER: [int(p) for p in params.postnumre]}})
    for lo, hi in params.postnummer_ranges:
        should.append({"range": {PATH_POSTNUMMER: {"gte": int(lo), "lte": int(hi)}}})
    if params.kommunekoder:
        should.append({"terms": {PATH_KOMMUNEKODE: [int(k) for k in params.kommunekoder]}})
    if not should:
        return None
    if len(should) == 1:
        return should[0]
    return {"bool": {"should": should, "minimum_should_match": 1}}


def _employee_clause(bands: list[str]) -> dict[str, Any] | None:
    """Match the requested employee bands across any reporting cadence."""
    if not bands:
        return None
    return {
        "bool": {
            "should": [{"terms": {path: bands}} for path in PATHS_EMPLOYEE_BAND],
            "minimum_should_match": 1,
        }
    }


def _status_clause(statuses: list[str]) -> dict[str, Any] | None:
    """Match active company statuses.

    ``sammensatStatus`` is an *analyzed text* field in the cvr-permanent index,
    so a ``terms`` filter (which does not analyze its input) never matches —
    the active value ``"NORMAL"`` is only reachable via ``match``. We OR a
    ``match`` per requested status in a ``should`` clause.
    """
    if not statuses:
        return None
    return {
        "bool": {
            "should": [{"match": {PATH_STATUS: s}} for s in statuses],
            "minimum_should_match": 1,
        }
    }


def build_es_query(params: SearchParameters) -> dict[str, Any]:
    """Build the Elasticsearch ``query`` body for a search definition."""
    filters: list[dict[str, Any]] = []

    if params.branchekoder:
        filters.append({"terms": {PATH_BRANCHEKODE: params.branchekoder}})

    geo = _geo_clause(params)
    if geo is not None:
        filters.append(geo)

    emp = _employee_clause(params.employee_bands)
    if emp is not None:
        filters.append(emp)

    status = _status_clause(params.statuses)
    if status is not None:
        filters.append(status)

    if not filters:
        return {"match_all": {}}
    return {"bool": {"filter": filters}}

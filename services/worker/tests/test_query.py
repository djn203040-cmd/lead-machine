from leadmachine.cvr.query import (
    ACTIVE_STATUSES,
    PATH_BRANCHEKODE,
    PATH_KOMMUNEKODE,
    PATH_POSTNUMMER,
    PATH_STATUS,
    PATHS_EMPLOYEE_BAND,
    SearchParameters,
    build_es_query,
)


def _filters(params: SearchParameters) -> list[dict]:
    return build_es_query(params)["bool"]["filter"]


def test_empty_params_match_all() -> None:
    params = SearchParameters(statuses=[])
    assert build_es_query(params) == {"match_all": {}}


def test_branchekoder_are_normalized_and_termed() -> None:
    params = SearchParameters(branchekoder=["96.02.10", "561010"], statuses=[])
    clause = _filters(params)[0]
    assert clause == {"terms": {PATH_BRANCHEKODE: ["960210", "561010"]}}


def test_default_status_is_active() -> None:
    params = SearchParameters(branchekoder=["960210"])
    status_clauses = [f for f in _filters(params) if f.get("terms", {}).get(PATH_STATUS)]
    assert status_clauses[0]["terms"][PATH_STATUS] == list(ACTIVE_STATUSES)


def test_postnumre_and_ranges_combine_into_should() -> None:
    params = SearchParameters(
        postnumre=[2200, 2300],
        postnummer_ranges=[[1000, 1999]],
        kommunekoder=[101],
        statuses=[],
    )
    geo = _filters(params)[0]["bool"]
    assert geo["minimum_should_match"] == 1
    shoulds = geo["should"]
    assert {"terms": {PATH_POSTNUMMER: [2200, 2300]}} in shoulds
    assert {"range": {PATH_POSTNUMMER: {"gte": 1000, "lte": 1999}}} in shoulds
    assert {"terms": {PATH_KOMMUNEKODE: [101]}} in shoulds


def test_single_geo_clause_is_not_wrapped() -> None:
    params = SearchParameters(postnumre=[2200], statuses=[])
    assert _filters(params)[0] == {"terms": {PATH_POSTNUMMER: [2200]}}


def test_employee_band_matches_any_cadence() -> None:
    params = SearchParameters(employee_bands=["ANTAL_2_4", "ANTAL_5_9"], statuses=[])
    emp = _filters(params)[0]["bool"]
    assert emp["minimum_should_match"] == 1
    paths = {list(s["terms"])[0] for s in emp["should"]}
    assert paths == set(PATHS_EMPLOYEE_BAND)
    for s in emp["should"]:
        assert list(s["terms"].values())[0] == ["ANTAL_2_4", "ANTAL_5_9"]


def test_full_query_has_all_clauses() -> None:
    params = SearchParameters(
        branchekoder=["960210"],
        postnumre=[2200],
        employee_bands=["ANTAL_2_4"],
    )
    filters = _filters(params)
    # branchekode + geo + employee + status
    assert len(filters) == 4


def test_postnummer_range_must_be_pair() -> None:
    import pytest

    with pytest.raises(ValueError):
        SearchParameters(postnummer_ranges=[[1000]])

from leadmachine.cvr import branchekoder as bk


def test_catalog_codes_are_unique_6digit_strings() -> None:
    codes = [b.code for b in bk.all_branches()]
    assert codes, "catalog is non-empty"
    assert len(codes) == len(set(codes)), "no duplicate codes"
    for c in codes:
        assert len(c) == 6 and c.isdigit(), f"{c} is not a 6-digit branchekode"


def test_plan_vetted_codes_present() -> None:
    # The codes explicitly listed in PLAN.md must be in the catalog.
    for code in ("960210", "561010", "432200", "862300", "931300"):
        assert bk.by_code(code) is not None, f"{code} missing from catalog"


def test_by_code_accepts_dotted_db07() -> None:
    frisor = bk.by_code("96.02.10")
    assert frisor is not None
    assert frisor.code == "960210"
    assert frisor.code_db07 == "96.02.10"
    assert frisor.label_da == "Frisørsaloner"


def test_normalize_code_strips_dots_and_spaces() -> None:
    assert bk.normalize_code(" 96.02.10 ") == "960210"
    assert bk.normalize_code("960210") == "960210"


def test_grouped_uses_known_groups() -> None:
    g = bk.grouped()
    assert set(g) <= set(bk.GROUPS) or set(bk.GROUPS) <= set(g)
    assert any(g.values()), "at least one group has branches"
    # every catalogued branche belongs to a declared group
    for b in bk.all_branches():
        assert b.group in bk.GROUPS

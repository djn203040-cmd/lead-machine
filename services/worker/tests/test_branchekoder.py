from leadmachine.cvr import branchekoder as bk


def test_catalog_codes_are_unique_6digit_strings() -> None:
    codes = [b.code for b in bk.all_branches()]
    assert codes, "catalog is non-empty"
    assert len(codes) == len(set(codes)), "no duplicate codes"
    for c in codes:
        assert len(c) == 6 and c.isdigit(), f"{c} is not a 6-digit branchekode"


def test_core_verticals_present() -> None:
    # Live-verified codes for core verticals must be in the catalog.
    for code in ("962100", "561110", "432200", "862300", "931300"):
        assert bk.by_code(code) is not None, f"{code} missing from catalog"


def test_by_code_accepts_dotted_db07() -> None:
    frisor = bk.by_code("96.21.00")
    assert frisor is not None
    assert frisor.code == "962100"
    assert frisor.code_db07 == "96.21.00"
    assert "Fris" in frisor.label_da  # friendly DB25 label, e.g. "Frisører & barbere"


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

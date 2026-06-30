from leadmachine.website.independence import business_key, is_not_independent


def test_business_key_drops_form_and_generic_words() -> None:
    tokens, slug = business_key("Bistro Solera ApS")
    assert "solera" in tokens
    assert "bistro" not in tokens  # generic hospitality word
    assert slug == "solera"


def test_sub_page_on_group_platform_is_not_independent() -> None:
    # The motivating case: a tenant sub-page on a shared group domain.
    assert is_not_independent(
        "foodfamilygroup.dk", "https://foodfamilygroup.dk/bistrosolera/", "Bistro Solera"
    )


def test_known_platform_host_flagged_even_without_name_in_path() -> None:
    assert is_not_independent("foodfamilygroup.dk", "https://foodfamilygroup.dk/", "Whatever ApS")


def test_own_domain_is_independent() -> None:
    assert not is_not_independent("bistrosolera.dk", "https://bistrosolera.dk/", "Bistro Solera")
    assert not is_not_independent("solera.dk", "https://solera.dk/menu", "Bistro Solera")


def test_unrelated_domain_without_name_in_path_left_alone() -> None:
    # Conservative: a different brand domain is graded on quality, not flagged.
    assert not is_not_independent("madhus.dk", "https://madhus.dk/", "Bistro Solera")


def test_short_or_missing_name_is_not_judged() -> None:
    assert not is_not_independent("portal.dk", "https://portal.dk/abc/", "Bar")
    assert not is_not_independent("portal.dk", "https://portal.dk/abc/", None)

from leadmachine.website.resolve import resolve_website


def test_empty_is_none() -> None:
    assert resolve_website(None).kind == "none"
    assert resolve_website("").kind == "none"
    assert resolve_website("   ").kind == "none"
    assert resolve_website("not-a-domain").kind == "none"


def test_social_hosts() -> None:
    for raw in ("https://facebook.com/minsalon", "www.instagram.com/x", "fb.me/abc"):
        r = resolve_website(raw)
        assert r.kind == "social", raw


def test_free_subdomain() -> None:
    assert resolve_website("https://minbutik.wixsite.com/shop").kind == "free_subdomain"
    assert resolve_website("http://foo.business.site").kind == "free_subdomain"
    assert resolve_website("sites.google.com/view/firma").kind == "free_subdomain"


def test_real_domain_is_normalized_to_https() -> None:
    r = resolve_website("frisoer-aarhus.dk")
    assert r.kind == "url"
    assert r.host == "frisoer-aarhus.dk"
    assert r.url == "https://frisoer-aarhus.dk/"


def test_www_is_stripped_for_host_but_kept_in_url() -> None:
    r = resolve_website("http://www.eksempel.dk/om")
    assert r.kind == "url"
    assert r.host == "eksempel.dk"
    assert r.url.startswith("https://www.eksempel.dk")

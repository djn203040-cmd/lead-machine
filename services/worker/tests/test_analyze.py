from leadmachine.website.analyze import analyze
from leadmachine.website.models import FetchResult

MODERN = """<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="WordPress 6.5.2">
<link rel="stylesheet" href="/wp-content/themes/x/style.css">
</head><body>
<nav><a href="/">Hjem</a><a href="/om-os">Om os</a><a href="/kontakt">Kontakt</a></nav>
<a href="https://facebook.com/minsalon">Facebook</a>
<script src="https://connect.facebook.net/da_DK/fbevents.js"></script>
<footer>&copy; 2026 Min Salon ApS</footer>
</body></html>"""

LEGACY = """<html><head>
<meta name="generator" content="Microsoft FrontPage 6.0">
</head><body bgcolor="#FFFFFF">
<font face="Arial" size="2">Velkommen til vores hjemmeside</font>
<table><tr><td>menu</td></tr></table>
<center>Copyright 2009 Gammelt Firma</center>
</body></html>"""


def test_modern_site_signals() -> None:
    s = analyze(FetchResult(final_url="https://minsalon.dk/", status=200, html=MODERN), host="minsalon.dk")
    assert s.has_viewport is True
    assert s.has_https is True
    assert s.legacy_markup is False
    assert s.cms == "wordpress"
    assert s.cms_version == "6.5.2"
    assert s.copyright_year == 2026
    assert s.has_fb_link is True
    assert s.fb_url == "https://facebook.com/minsalon"
    assert s.has_meta_pixel is True
    assert s.is_one_page is False


def test_legacy_site_signals() -> None:
    s = analyze(FetchResult(final_url="http://gammelt.dk/", status=200, html=LEGACY, tls_ok=False), host="gammelt.dk")
    assert s.has_viewport is False
    assert s.has_https is False
    assert s.legacy_markup is True
    assert "font_tag" in s.legacy_reasons
    assert "legacy_generator" in s.legacy_reasons
    assert s.copyright_year == 2009


def test_wix_builder_detected() -> None:
    html = '<html><body><script src="https://static.wixstatic.com/x.js"></script></body></html>'
    s = analyze(FetchResult(final_url="https://x.dk/", status=200, html=html))
    assert s.cms == "wix"


def test_wix_detected_via_generator_meta() -> None:
    html = '<html><head><meta name="generator" content="Wix.com Website Builder"></head><body></body></html>'
    s = analyze(FetchResult(final_url="https://x.dk/", status=200, html=html))
    assert s.cms == "wix"


def test_one_page_site() -> None:
    html = (
        '<html><head><meta name="viewport" content="width=device-width"></head>'
        '<body><a href="#top">Top</a><a href="/">Home</a><a href="mailto:x@y.dk">Mail</a></body></html>'
    )
    s = analyze(FetchResult(final_url="https://x.dk/", status=200, html=html), host="x.dk")
    assert s.is_one_page is True

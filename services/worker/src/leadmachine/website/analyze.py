"""Static website-quality signals from captured HTML (M2, issue #20).

Pure HTML/header parsing (stdlib ``html.parser`` — no native deps) for the
Tier-1/Tier-2 signals in research §1.2/§1.4: responsive viewport, HTTPS, legacy
hand-coded markup, CMS/builder, copyright year, one-page, Facebook link and Meta
Pixel.

CMS detection is a focused DIY fingerprint of the common stacks; the
``enthec/webappanalyzer`` rule DB can be swapped in for breadth later.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from .models import FetchResult, WebsiteSignals

_LEGACY_GENERATORS = ("frontpage", "dreamweaver", "golive", "publisher", "microsoft word", "namo")
_COPYRIGHT_RE = re.compile(
    r"(?:©|&copy;|&#169;|copyright)\s*(?:\d{4}\s*[–-]\s*)?(\d{4})", re.IGNORECASE
)


class _Collector(HTMLParser):
    """Collects the bits of an HTML document we score on."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metas: dict[str, str] = {}
        self.script_srcs: list[str] = []
        self.link_hrefs: list[str] = []
        self.anchors: list[str] = []
        self.has_font = False
        self.has_frameset = False
        self.has_marquee = False
        self.has_table = False
        self.has_layout_attr = False  # bgcolor / align on block elements
        self._text: list[str] = []
        self._in_text = True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("name") or a.get("property") or a.get("http-equiv") or "").lower()
            if key:
                self.metas[key] = a.get("content", "")
        elif tag == "script" and a.get("src"):
            self.script_srcs.append(a["src"])
        elif tag == "link":
            if a.get("href"):
                self.link_hrefs.append(a["href"])
        elif tag == "a" and a.get("href"):
            self.anchors.append(a["href"])
        elif tag == "font":
            self.has_font = True
        elif tag in ("frameset", "frame"):
            self.has_frameset = True
        elif tag == "marquee":
            self.has_marquee = True
        elif tag == "table":
            self.has_table = True
        if tag in ("table", "td", "tr", "body") and ("bgcolor" in a or a.get("align")):
            self.has_layout_attr = True

    def handle_data(self, data: str) -> None:
        chunk = data.strip()
        if chunk:
            self._text.append(chunk)

    @property
    def text(self) -> str:
        return " ".join(self._text)


def _detect_cms(html: str, headers: dict[str, str], metas: dict[str, str]) -> tuple[str | None, str | None]:
    generator = metas.get("generator", "")
    gen_l = generator.lower()
    h = html.lower()

    if "/wp-content/" in h or "/wp-includes/" in h or "/wp-json/" in h or "x-pingback" in headers or gen_l.startswith("wordpress"):
        version = None
        m = re.search(r"wordpress\s+([\d.]+)", gen_l)
        if m:
            version = m.group(1)
        return "wordpress", version
    if "static.wixstatic.com" in h or "wix-warmup-data" in h or "x-wix-request-id" in headers or "wix.com" in gen_l:
        return "wix", None
    if "static1.squarespace.com" in h or "squarespace-cdn.com" in h or "squarespace_context" in h or gen_l.startswith("squarespace"):
        return "squarespace", None
    if "assets.webflow.com" in h or ".webflow.io" in h or gen_l.startswith("webflow"):
        return "webflow", None
    if "cdn.shopify.com" in h or "/cdn/shop/" in h or "shopify.theme" in h:
        return "shopify", None
    if gen_l.startswith("joomla"):
        return "joomla", None
    if gen_l.startswith("drupal"):
        return "drupal", None
    return None, None


def _detect_legacy(c: _Collector, metas: dict[str, str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if c.has_font:
        reasons.append("font_tag")
    if c.has_frameset:
        reasons.append("frameset")
    if c.has_marquee:
        reasons.append("marquee")
    gen_l = metas.get("generator", "").lower()
    if any(g in gen_l for g in _LEGACY_GENERATORS):
        reasons.append("legacy_generator")
    has_viewport = "viewport" in metas
    if c.has_table and not has_viewport and c.has_layout_attr:
        reasons.append("table_layout")
    return (bool(reasons), reasons)


def _copyright_year(text: str) -> int | None:
    years = [int(y) for y in _COPYRIGHT_RE.findall(text)]
    return max(years) if years else None


def _detect_facebook(anchors: list[str], html: str) -> tuple[bool, str | None]:
    for href in anchors:
        low = href.lower()
        if "facebook.com/" in low and "/plugins/" not in low and "sharer" not in low:
            return True, href
    return ("facebook.com/" in html.lower(), None)


def _detect_pixel(html: str, scripts: list[str]) -> bool:
    h = html.lower()
    if "connect.facebook.net" in h or "fbevents.js" in h or "fbq(" in h:
        return True
    return any("connect.facebook.net" in s.lower() for s in scripts)


def _detect_one_page(anchors: list[str], host: str | None) -> bool:
    paths: set[str] = set()
    for href in anchors:
        low = href.strip().lower()
        if not low or low.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        parts = urlsplit(href)
        if parts.netloc and host and host not in parts.netloc.lower():
            continue  # external link
        path = (parts.path or "/").rstrip("/") or "/"
        if path != "/":
            paths.add(path)
    return len(paths) <= 1


def analyze(result: FetchResult, host: str | None = None) -> WebsiteSignals:
    """Extract quality signals from a successful fetch."""
    collector = _Collector()
    try:
        collector.feed(result.html or "")
    except Exception:
        pass  # tolerate malformed HTML; use whatever was parsed

    metas = collector.metas
    cms, cms_version = _detect_cms(result.html, result.headers, metas)
    legacy, legacy_reasons = _detect_legacy(collector, metas)
    has_fb, fb_url = _detect_facebook(collector.anchors, result.html)

    return WebsiteSignals(
        has_viewport="viewport" in metas,
        has_https=result.has_https,
        legacy_markup=legacy,
        legacy_reasons=legacy_reasons,
        cms=cms,
        cms_version=cms_version,
        copyright_year=_copyright_year(collector.text or result.html),
        is_one_page=_detect_one_page(collector.anchors, host),
        has_fb_link=has_fb,
        fb_url=fb_url,
        has_meta_pixel=_detect_pixel(result.html, collector.script_srcs),
    )

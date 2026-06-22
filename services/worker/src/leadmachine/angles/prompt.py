"""Prompt construction for Danish sales-angle generation (M6).

Turns a :class:`LeadForAngle` into a factual Danish brief + a fixed system
prompt. Kept pure (no network, no SDK) so it's unit-testable on its own.
"""

from __future__ import annotations

from typing import Any

from .models import LeadForAngle

SYSTEM_PROMPT = """\
You write phone-call sales angles for a Danish web-design agency. The agency \
builds modern websites (roughly 10,000–20,000 DKK) for small local Danish \
businesses and later upsells systems and automation. The strongest leads are \
businesses with no website, a dead or parked domain, a Facebook-only presence, \
or a bad/outdated site.

You are given a factual brief about ONE business. Produce a concise pitch a \
Danish salesperson can use to open a COLD PHONE CALL. B2B cold calls are legal \
in Denmark; this is for a phone call, never an email.

Return JSON with these fields, all written in natural, professional Danish:
- summary_da: 1–2 sentences on who the business is and why they are a good fit now.
- weaknesses_da: the concrete, specific problems with their current web presence, \
using only the facts in the brief.
- angle_da: the core sales angle — how a new website helps THIS business win more \
local customers. 2–3 benefit-led sentences.
- opening_line_da: one natural spoken opening sentence for the call — friendly, \
specific to their situation, not generic sales boilerplate.
- competitor_name: a named competitor ONLY if one appears in the brief; otherwise "".
- competitor_angle_type: "fomo" if the angle leans on competitors being more \
visible online, "first_mover" if it leans on being first/best online locally, \
or "none".

Rules: ground every claim in the brief. Never invent facts, numbers, awards, or \
competitor names. No emojis. Keep it tight — this is a call opener, not a brochure."""

# website_need → Danish label for the brief.
_NEED_DA: dict[str, str] = {
    "none": "Ingen hjemmeside",
    "dead": "Dødt domæne",
    "parked": "Parkeret domæne",
    "facebook_only": "Kun en Facebook-side, ingen rigtig hjemmeside",
    "bad": "Dårlig hjemmeside",
    "outdated": "Forældet hjemmeside",
    "modern": "Moderne hjemmeside",
    "unknown": "Ukendt",
}

_FACTOR_DA: dict[str, str] = {
    "website_need": "Hjemmesidebehov",
    "budget": "Budget",
    "presence": "Online tilstedeværelse",
    "industry": "Brancheegnethed",
    "recency": "Aktualitet",
}


def _weaknesses(lead: LeadForAngle) -> list[str]:
    """Human-readable Danish web-presence weaknesses, from website_need + signals."""
    need = lead.website_need
    if need in ("none", "dead", "parked", "facebook_only"):
        return [_NEED_DA.get(need, need)]

    out: list[str] = []
    signals = (lead.website or {}).get("signals") or {}
    pagespeed = (lead.website or {}).get("pagespeed") or {}
    if signals.get("has_viewport") is False:
        out.append("ikke mobilvenlig (mangler viewport)")
    if signals.get("has_https") is False:
        out.append("ingen HTTPS/sikkerhed")
    if signals.get("legacy_markup"):
        out.append("forældet teknik/kodning")
    year = signals.get("copyright_year")
    if isinstance(year, int):
        out.append(f"copyright fra {year}")
    if signals.get("is_one_page"):
        out.append("kun én side")
    perf = pagespeed.get("performance")
    if isinstance(perf, (int, float)) and perf < 50:
        out.append("meget langsom på mobil")
    if not out and need == "outdated":
        out.append("virker forældet")
    return out


def _social_line(social: dict[str, Any]) -> str | None:
    bits: list[str] = []
    if social.get("has_fb_page"):
        bits.append("Facebook-side")
    if social.get("has_meta_pixel"):
        bits.append("Meta Pixel (kører annoncer)")
    return ", ".join(bits) if bits else None


def _revenue_line(financial: dict[str, Any]) -> str | None:
    est = (financial or {}).get("revenue_estimate") or {}
    value = est.get("value")
    if not isinstance(value, (int, float)):
        return None
    confidence = est.get("confidence")
    suffix = f" ({confidence} sikkerhed)" if confidence else ""
    return f"ca. {round(value):,} DKK{suffix}".replace(",", ".")


def _factor_line(score_breakdown: dict[str, Any]) -> str | None:
    factors = (score_breakdown or {}).get("factors") or {}
    parts: list[str] = []
    for key, label in _FACTOR_DA.items():
        f = factors.get(key)
        if isinstance(f, dict) and isinstance(f.get("points"), (int, float)):
            parts.append(f"{label} {f['points']}/{f.get('max', '?')}")
    return ", ".join(parts) if parts else None


def build_user_prompt(lead: LeadForAngle) -> str:
    """A compact Danish brief describing the lead's signals."""
    lines = [f"Virksomhed: {lead.company_name}"]
    if lead.branche_text:
        lines.append(f"Branche: {lead.branche_text}")
    if lead.city:
        lines.append(f"By: {lead.city}")
    if lead.employees is not None:
        lines.append(f"Antal ansatte: {lead.employees}")
    if lead.score is not None:
        lines.append(f"Lead-score (0–100): {lead.score}")

    lines.append(f"Hjemmeside-status: {_NEED_DA.get(lead.website_need, lead.website_need)}")

    weaknesses = _weaknesses(lead)
    if weaknesses:
        lines.append("Svagheder ved nuværende online-tilstedeværelse:")
        lines.extend(f"- {w}" for w in weaknesses)

    revenue = _revenue_line(lead.financial)
    if revenue:
        lines.append(f"Estimeret omsætning: {revenue}")

    social = _social_line(lead.social)
    if social:
        lines.append(f"Online-tilstedeværelse: {social}")

    factors = _factor_line(lead.score_breakdown)
    if factors:
        lines.append(f"Hvorfor det er et godt lead (score-faktorer): {factors}")

    return "\n".join(lines)


def build_prompt(lead: LeadForAngle) -> tuple[str, str]:
    """Return ``(system, user)`` prompts for one lead."""
    return SYSTEM_PROMPT, build_user_prompt(lead)

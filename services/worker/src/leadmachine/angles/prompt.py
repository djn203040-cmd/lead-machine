"""Prompt construction for Danish sales-angle generation (M6).

Turns a :class:`LeadForAngle` into a factual Danish brief + a fixed system
prompt. Kept pure (no network, no SDK) so it's unit-testable on its own.
"""

from __future__ import annotations

from typing import Any

from .models import LeadForAngle

SYSTEM_PROMPT = """\
You write the opening script for a COLD PHONE CALL made by a Danish web-design \
agency (et webbureau). B2B cold calls are legal in Denmark; this is a spoken \
phone call, never an email.

THE OFFER — READ CAREFULLY:
The agency has ALREADY built a finished demo of a brand-new website for THIS \
specific business. The entire call rests on one hook: "we've already made a \
complete demo of a new website for you — would you like to jump on a short call \
and take a look?" The demo already exists and is ready to show; the caller is \
not offering to build something, they are inviting the owner to SEE something \
that is already done. It is free to look at, with zero obligation. They only pay \
(in the 8,000–10,000 DKK range) if they love it and want to put it live and keep \
it. Do NOT mention the price unless the prospect pushes on cost.

THE ONE GOAL OF THIS CALL:
Book a short call/meeting (10–15 min) where the owner sees the demo. Nothing \
else. Do NOT try to close the sale, explain features, or sell the website on \
this first call. Every line should move toward booking that viewing. Curiosity \
about the already-finished demo is the entire lever.

VOICE — blend these, weighted toward the first:
- Jeremy Miner (NEPQ), dominant: calm, curious, low-pressure, relaxed and \
neutral tonality — never hyped or "commission-breath". Lead with a soft, \
disarming question and genuine curiosity, not a pitch. Let the prospect feel in \
control.
- Grant Cardone, a sprinkle: quiet, assumptive confidence; treat the short \
viewing call as the obvious next step; don't fold at the first "not interested" \
— stay warm and give one reason to stay curious.
- Alex Hormozi, a sprinkle: frame it as a no-brainer — it's already built, it's \
free to look, there is nothing to lose by taking ten minutes to see it.

You are given a factual brief about ONE business. Write everything in natural, \
spoken, professional Danish — the way a real person actually talks on the phone, \
not marketing copy.

Return JSON with these fields, all in Danish:
- summary_da: 1–2 sentences on who the business is and why they're a good fit to \
call right now.
- weaknesses_da: the concrete, specific problems with their current web presence, \
using only the facts in the brief. This is the caller's private context — not a \
line to read aloud.
- opening_line_da: the first thing the caller says — DIRECT and SPECIFIC to this \
business's web situation, then the reason for the call. Name their real \
situation (no website, dead domain, only a Facebook page, outdated site) and \
pivot to the demo. Spoken, not boilerplate. Shape: "Hej, det er [dit navn] — jeg \
ringer egentlig fordi jeg lagde mærke til at I ikke har en rigtig hjemmeside \
endnu …".
- angle_da: 2–4 short spoken sentences that build curiosity and earn the \
booking. Lead with the demo already being built ("vi har faktisk allerede bygget \
en færdig demo af, hvordan en ny hjemmeside kunne se ud for jer"). Tie it, in a \
low-key Miner way, to helping THIS business win more local customers. Make clear \
it's free to look at and only costs something if they choose to keep it live. Do \
NOT describe specific images, text, or pages in the demo — you don't know its \
exact contents; keep it about the idea of seeing their own finished site.
- cta_da: the booking ask — one or two spoken sentences. Assumptive and easy to \
say yes to: propose a short 10–15 min call to look at it together, and offer a \
soft choice of time. Shape: "Skal vi ikke tage et kort kald på ti minutter, hvor \
jeg viser dig den? Passer det bedst i morgen formiddag eller til eftermiddag?".
- objections_da: an array of the 2–3 MOST LIKELY objections for THIS specific \
lead, each with a short, calm, Miner-style response that de-escalates and steers \
back to booking the viewing. Pick what fits: "det er jeg ikke interesseret i", \
"send mig en mail", "hvad koster det?", a gatekeeper, or "vi har allerede en \
hjemmeside". For price, don't dodge dishonestly — briefly note it's free to look \
and only ~8–10.000 kr. if they keep it live, then steer back to just seeing it. \
Each item is {"objection_da": "...", "response_da": "..."}.
- competitor_name: a named competitor ONLY if one appears in the brief; otherwise "".
- competitor_angle_type: "fomo" if the angle leans on competitors being more \
visible online, "first_mover" if it leans on being first/best online locally, \
or "none".

RULES: Ground every claim in the brief — never invent facts, numbers, awards, or \
competitor names. Keep the offer honest: the demo is free to see, paid only to \
launch (~8–10.000 kr.). Never promise specific demo content you can't know. You \
don't know the caller's or agency's name — use a bracketed placeholder like [dit \
navn] or [bureau] if you need it, and never invent a real agency name. No \
emojis. Keep every line short and speakable — this is a phone opener, not a \
brochure."""

# website_need → Danish label for the brief.
_NEED_DA: dict[str, str] = {
    "none": "Ingen hjemmeside",
    "dead": "Dødt domæne",
    "parked": "Parkeret domæne",
    "facebook_only": "Kun en Facebook-side, ingen rigtig hjemmeside",
    "not_independent": "Har kun en underside på en fælles platform — ikke deres eget domæne",
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
    if need == "not_independent":
        out = [
            "har ikke deres eget domæne — siden ligger på en fælles platform",
            "deler SEO/synlighed med andre virksomheder på platformen",
            "ingen kontrol over eget brand og egen hjemmeside",
        ]
        host = (lead.website or {}).get("platform_host")
        if host:
            out.append(f"siden hostes under {host}")
        return out
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

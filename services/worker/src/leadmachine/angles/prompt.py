"""Prompt construction for Danish sales-angle generation (M6).

Turns a :class:`LeadForAngle` into a factual Danish brief + a fixed system
prompt. Kept pure (no network, no SDK) so it's unit-testable on its own.

**Angle v3 — the operations/savings offer.** We no longer sell a website. We
follow the business for a period, build the systems that remove its manual work,
and take 20% of what is actually saved. The brief's centre of gravity is
therefore the **savings math in DKK** (see :mod:`..financial.savings`); the
website/online status survives only as a private read on how digitally mature
the business is — never as the pitch.
"""

from __future__ import annotations

from typing import Any

from ..financial.savings import FEE_SHARE, SavingsEstimate, estimate_savings, levers_for
from .models import LeadForAngle

SYSTEM_PROMPT = """\
You write the opening script for a COLD PHONE CALL made by a small Danish firm \
that builds operational systems for local businesses. B2B cold calls are legal \
in Denmark; this is a spoken phone call, never an email.

THE OFFER — READ CAREFULLY:
The caller does NOT sell websites, design, or marketing. The offer is this:
1. They follow the business for a period — they look at how it actually runs day \
to day and find where the hours and the kroner disappear (manual admin, phone \
orders, planning, follow-up that never happens, double work).
2. They build the systems that remove that work — automation, booking, \
follow-up, planning, reporting. Practical plumbing, not a software project the \
owner has to run.
3. The business pays **20% of what is actually saved** — measured and \
documented against how things ran before. Nothing up front, no fixed fee, no \
subscription, no binding. If nothing is saved, nothing is paid. The business \
keeps the other 80%, permanently.
That risk-free, share-of-savings structure IS the hook. Lead with what it does \
for them (time and money back), not with technology.

THE ONE GOAL OF THIS CALL:
Book a short call/meeting (10–15 min) where the caller and the owner look \
together at where the time goes. Nothing else. Do NOT try to close, do NOT \
explain the technology, do NOT scope the work on this first call. Every line \
moves toward booking that conversation.

THE MONEY — HANDLE HONESTLY:
The brief may contain "Realistisk årlig besparelse" — a DKK band estimated from \
the business's sector and size, plus the matching 20% fee. That number is an \
ESTIMATE from public data, not their accounts.
- Use it as a typical range: "hos virksomheder på jeres størrelse i jeres branche \
plejer der at ligge et sted mellem X og Y kroner om året i spildtid og \
dobbeltarbejde" — then invite them to check whether it holds for them.
- NEVER promise a specific saving, never say "vi sparer jer X", never claim to \
know their numbers. Curiosity, not a guarantee.
- Mention that they only pay 20% of what is actually saved — that is what makes \
the number safe to talk about.
- If the brief says there is no revenue estimate, do NOT invent any figure. \
Talk about hours and manual work instead, and propose finding the number together.

NOT A WEBSITE PITCH:
The brief's "Teknisk modenhed" section is private background — it tells the \
caller how digital the business is and how technical to be. Never open with \
their website, never offer to build or redesign one, never treat a missing or \
bad website as the problem you're calling about. If the owner brings up their \
website, it's fine to acknowledge it and steer back to where their time goes.

WHO ANSWERS THE PHONE:
The brief includes a "Telefonnummer-type" line saying what kind of number the \
caller is dialing. Adapt everything to who actually picks up:
- Mobilnummer: assume the OWNER answers directly. Write the opener straight to \
them, personal and specific.
- Fastnet/hovednummer or 70/80-nummer: assume an employee or receptionist \
answers — likely NOT the decision maker, possibly mid-rush. The \
opening_line_da must work on whoever picks up: one short line on why you're \
calling — you help businesses like theirs get manual timespild ud af hverdagen, \
and they only pay a share of what's saved — then ask for the right person, e.g. \
"hvem er den rigtige at tale med om, hvordan I får driften til at køre?". Never \
pitch the full angle to a gatekeeper. angle_da then assumes the caller has \
reached the owner. Include a gatekeeper objection in objections_da (e.g. "ejeren \
er her ikke" → get a name and the best time to call back, calmly). Respect the \
person's time — offer to call back if they sound busy.
If the line is missing, write for the owner answering directly.

VOICE — blend these, weighted toward the first:
- Jeremy Miner (NEPQ), dominant: calm, curious, low-pressure, relaxed and \
neutral tonality — never hyped or "commission-breath". Lead with a soft, \
disarming question and genuine curiosity, not a pitch. Let the prospect feel in \
control, and let THEM name what eats their time.
- Grant Cardone, a sprinkle: quiet, assumptive confidence; treat the short \
conversation as the obvious next step; don't fold at the first "not interested" \
— stay warm and give one reason to stay curious.
- Alex Hormozi, a sprinkle: frame it as a no-brainer — they pay nothing unless \
money is actually saved, and they keep 80% of it.

You are given a factual brief about ONE business. Write everything in natural, \
spoken, professional Danish — the way a real person actually talks on the phone, \
not marketing copy.

Return JSON with these fields, all in Danish:
- summary_da: 1–2 sentences on who the business is and why they're a good fit to \
call right now (size, sector, what kind of manual load that usually means).
- weaknesses_da: the caller's PRIVATE notes — where the time and money most \
likely leak in this specific business, plus the savings math (estimated annual \
saving band, our 20% share, what they keep). Bullet-ish and concrete. This is \
never read aloud.
- opening_line_da: the first thing the caller says — spoken, short, and \
disarming. Say who you are, be honest that it's a cold call, and give the real \
reason in one line tied to THIS business's everyday reality (their sector's \
typical time drain). Do not mention their website. Shape: "Hej, det er [dit \
navn] — jeg ringer helt koldt, må jeg få tredive sekunder til at sige hvorfor?".
- angle_da: 2–4 short spoken sentences that build curiosity and earn the \
booking. Cover, in a low-key Miner way: that you follow the business for a \
period to see where the hours go, that you build the systems that remove that \
work, and that they only pay 20% of what is actually saved — nothing up front. \
Use the estimated DKK range as a typical range for their size if the brief has \
one. End on curiosity, not a close.
- cta_da: the booking ask — one or two spoken sentences. Assumptive and easy to \
say yes to: propose a short 10–15 min conversation about where their time goes, \
and offer a soft choice of time. Shape: "Skal vi ikke tage ti minutter, hvor jeg \
spørger ind til, hvordan I kører det i dag? Passer det bedst i morgen formiddag \
eller til eftermiddag?".
- objections_da: an array of the 2–3 MOST LIKELY objections for THIS specific \
lead, each with a short, calm, Miner-style response that de-escalates and steers \
back to booking. Pick what fits: "det er jeg ikke interesseret i", "vi har ikke \
tid", "hvad koster det?", "hvordan kan I vide, hvad I kan spare os?", "vi har \
allerede styr på det", "send mig en mail", or a gatekeeper. For price: nothing up \
front, 20% of what is actually documented as saved, nothing saved = nothing paid. \
For scepticism about the number: agree openly that you don't know their business \
yet — that is exactly why the first step is to look, not to sell. Each item is \
{"objection_da": "...", "response_da": "..."}.
- competitor_name: a named competitor ONLY if one appears in the brief; otherwise "".
- competitor_angle_type: "fomo" if the angle leans on others in their trade \
already automating this, "first_mover" if it leans on being first locally to run \
things this way, or "none".

RULES: Ground every claim in the brief — never invent facts, numbers, awards, or \
competitor names. Never promise a specific saving; the DKK band is a typical \
range and the fee is charged only on what is measured. Never sell a website. You \
don't know the caller's or the firm's name — use a bracketed placeholder like \
[dit navn] or [firma] if you need it, and never invent a real company name. No \
emojis. Keep every line short and speakable — this is a phone opener, not a \
brochure."""

# website_need → Danish label for the brief. Background only under angle v3:
# it reads as digital maturity, not as the thing being sold.
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

# website_need → what it says about how digitally mature the business is, and
# how technical the caller should be. Private context for the caller.
_MATURITY_DA: dict[str, str] = {
    "none": (
        "lav digital modenhed — forvent telefon, papir og hukommelse i driften. "
        "Stor upside, men tal helt konkret og undgå fagsprog og engelske ord"
    ),
    "dead": (
        "lav digital modenhed — de har prøvet noget digitalt, men det er faldet fra "
        "hinanden. Hold sproget jordnært"
    ),
    "parked": (
        "lav digital modenhed — domænet står bare parkeret. Hold sproget jordnært"
    ),
    "facebook_only": (
        "markedsfører online, men har ingen egentlig infrastruktur — meget køres "
        "sandsynligvis manuelt bagved"
    ),
    "not_independent": (
        "ligger på en fælles platform — begrænset eget digitalt setup, meget køres "
        "sandsynligvis manuelt"
    ),
    "bad": (
        "har taget digitale skridt, men vedligeholder dem ikke — typisk også manuelle "
        "processer indenfor"
    ),
    "outdated": (
        "har taget digitale skridt for år tilbage og er ikke fulgt med — typisk også "
        "manuelle processer indenfor"
    ),
    "modern": (
        "digitalt med — de forstår værktøjer, så systemsnak er en let samtale. "
        "Til gengæld har de måske allerede noget på plads; spørg ind i stedet for "
        "at antage"
    ),
}

# phone_type → Danish "who answers" line for the brief.
_PHONE_TYPE_DA: dict[str, str] = {
    "mobile": "Mobilnummer — ringer sandsynligvis direkte til ejeren",
    "landline": (
        "Fastnet/hovednummer — sandsynligvis butikkens hovedtelefon; "
        "en medarbejder eller reception kan tage den (gatekeeper)"
    ),
    "service": (
        "70/80-nummer — virksomhedens omstilling/hovednummer; "
        "helt sikkert ikke ejerens egen telefon (gatekeeper)"
    ),
}

_FACTOR_DA: dict[str, str] = {
    "savings": "Besparelsespotentiale",
    "industry": "Brancheegnethed",
    "tech": "Digital modenhed",
    "presence": "Online tilstedeværelse",
    "size": "Størrelse/kompleksitet",
    "recency": "Aktualitet",
}


def _dkk(value: float | int) -> str:
    """Danish thousands-separated DKK, e.g. ``110.000``."""
    return f"{round(value):,}".replace(",", ".")


def _maturity_line(lead: LeadForAngle) -> str:
    """One private line on how digitally mature the business looks."""
    reading = _MATURITY_DA.get(lead.website_need)
    quality = (lead.website or {}).get("quality") or {}
    tier = quality.get("tier")
    if tier in ("modern", "premium") and lead.website_need not in ("none", "dead", "parked"):
        return _MATURITY_DA["modern"]
    return reading or "ukendt digital modenhed — læs den på, hvordan de svarer i telefonen"


def _social_line(social: dict[str, Any]) -> str | None:
    bits: list[str] = []
    if social.get("has_fb_page"):
        bits.append("Facebook-side")
    if social.get("has_meta_pixel"):
        bits.append("Meta Pixel (kører annoncer — bruger allerede penge på vækst)")
    return ", ".join(bits) if bits else None


def _revenue_line(financial: dict[str, Any]) -> str | None:
    est = (financial or {}).get("revenue_estimate") or {}
    value = est.get("value")
    if not isinstance(value, (int, float)):
        return None
    confidence = est.get("confidence")
    suffix = f" ({confidence} sikkerhed)" if confidence else ""
    return f"ca. {_dkk(value)} DKK{suffix}"


def _savings_block(savings: SavingsEstimate, employees: int | None) -> list[str]:
    """The heart of the brief: what we can realistically save, and our cut."""
    fee_pct = round(FEE_SHARE * 100)
    lines = [
        (
            f"Realistisk årlig besparelse (ca. {round(savings.rate * 100)}% af omsætningen, "
            f"branchejusteret): {_dkk(savings.annual_low)}–{_dkk(savings.annual_high)} DKK "
            f"om året ({savings.confidence} sikkerhed)"
        ),
        (
            f"Jeres honorar ({fee_pct}% af det faktisk sparede): "
            f"{_dkk(savings.fee_low)}–{_dkk(savings.fee_high)} DKK om året"
        ),
        (
            f"Virksomheden beholder selv: {_dkk(savings.keeps_low)}–"
            f"{_dkk(savings.keeps_high)} DKK om året"
        ),
    ]
    if savings.capped_by == "headcount":
        lines.append(
            "Bemærk: tallet er skåret ned efter antal ansatte — der er kun så mange "
            "hænder at frigøre tid fra"
        )
    if employees is None:
        lines.append(
            "Bemærk: antal ansatte er ukendt, så tallet er IKKE afstemt efter, hvor mange "
            "hænder der er. Spørg tidligt til, hvor mange de er — og skru forventningen "
            "ned, hvis de er få"
        )
    if savings.capped_by == "gross_profit":
        lines.append(
            "Bemærk: tallet er skåret ned efter deres bruttofortjeneste — "
            "der er ikke mere at hente end det, de faktisk tjener på omsætningen"
        )
    lines.append(
        "VIGTIGT: tallene er estimeret ud fra branche og størrelse — ikke deres regnskab. "
        "Præsentér dem som et typisk spænd for virksomheder på deres størrelse, aldrig "
        "som et løfte"
    )
    return lines


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

    phone_type = _PHONE_TYPE_DA.get(lead.phone_type or "")
    if phone_type:
        lines.append(f"Telefonnummer-type: {phone_type}")

    # --- økonomi + besparelsespotentiale (the offer's centre of gravity) ---
    lines.append("")
    lines.append("ØKONOMI OG BESPARELSESPOTENTIALE:")
    revenue = _revenue_line(lead.financial)
    if revenue:
        lines.append(f"Estimeret omsætning: {revenue}")
    gross = (lead.financial or {}).get("gross_profit")
    if isinstance(gross, (int, float)) and not isinstance(gross, bool):
        lines.append(f"Bruttofortjeneste (regnskab): {_dkk(gross)} DKK")

    savings = estimate_savings(lead.financial, lead.branchekode, lead.employees)
    if savings is not None:
        lines.extend(_savings_block(savings, lead.employees))
    else:
        lines.append(
            "Intet omsætningsestimat tilgængeligt — brug IKKE konkrete kronebeløb i denne "
            "samtale. Spørg i stedet ind til, hvor timerne går, og foreslå at regne på det "
            "sammen"
        )

    # --- where the time most likely goes (hypotheses, not claims) ---
    lines.append("")
    lines.append("SANDSYNLIGE TIDSRØVERE I DENNE BRANCHE (hypoteser — spørg, påstå ikke):")
    lines.extend(f"- {lever}" for lever in levers_for(lead.branchekode))

    # --- private read on digital maturity (never the pitch) ---
    lines.append("")
    lines.append("TEKNISK MODENHED (kun baggrund for dig — må ikke bruges som salgsvinkel):")
    lines.append(f"- Hjemmeside: {_NEED_DA.get(lead.website_need, lead.website_need)}")
    social = _social_line(lead.social)
    if social:
        lines.append(f"- Online tilstedeværelse: {social}")
    lines.append(f"- Læsning: {_maturity_line(lead)}")

    factors = _factor_line(lead.score_breakdown)
    if factors:
        lines.append("")
        lines.append(f"Hvorfor det er et godt lead (score-faktorer): {factors}")

    return "\n".join(lines)


def _factor_line(score_breakdown: dict[str, Any]) -> str | None:
    factors = (score_breakdown or {}).get("factors") or {}
    parts: list[str] = []
    for key, label in _FACTOR_DA.items():
        f = factors.get(key)
        if isinstance(f, dict) and isinstance(f.get("points"), (int, float)):
            parts.append(f"{label} {f['points']}/{f.get('max', '?')}")
    return ", ".join(parts) if parts else None


def build_prompt(lead: LeadForAngle) -> tuple[str, str]:
    """Return ``(system, user)`` prompts for one lead."""
    return SYSTEM_PROMPT, build_user_prompt(lead)

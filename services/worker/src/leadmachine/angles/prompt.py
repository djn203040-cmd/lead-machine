"""Prompt construction for Danish sales-angle generation (M6).

Turns a :class:`LeadForAngle` into a factual Danish brief + a fixed system
prompt. Kept pure (no network, no SDK) so it's unit-testable on its own.

**Angle v4 — notes for a fixed script.** We no longer sell a website, and the
model no longer writes the spoken script: the opener, pitch, price answer and
booking ask are hard-coded in the dialer (``apps/web/lib/script.ts``) and only
the first name and the savings figure vary. The model supplies what is specific
to the lead — the private "where the time leaks" notes and the tailored
objection responses. The offer: follow the business remotely for 30 days, build
what closes the holes, and take 20% of one year's documented saving, once. The
brief's centre of gravity is therefore the **savings math in DKK** (see
:mod:`..financial.savings`); the website/online status survives only as a
private read on how digitally mature the business is — never as the pitch.
"""

from __future__ import annotations

from typing import Any

from ..financial.savings import FEE_SHARE, SavingsEstimate, estimate_savings, levers_for
from .models import LeadForAngle

SYSTEM_PROMPT = """\
You prepare the CALLER'S NOTES for a COLD PHONE CALL made by a small Danish firm \
that builds operational systems for local businesses. B2B cold calls are legal \
in Denmark; this is a spoken phone call, never an email.

THE SCRIPT IS FIXED — YOU DO NOT WRITE IT:
The caller reads the same opener, pitch, price answer and booking ask on every \
call. It is hard-coded in the dialer; only the owner's first name and the \
savings figure change. You are given it here so your notes and objection \
responses fit what the caller has just said out loud — never contradict it, \
never rewrite it, never repeat it in your output.

  Åbning (ejer): "Hej, det er [navn]. Jeg ved godt det er pisse irriterende at \
blive ringet op af en, man ikke har bedt om, men må jeg få 30 sekunder af din \
tid?"
  Åbning (medarbejder/reception): "Hej, det er [navn]. Jeg ved godt jeg ringer \
helt uopfordret — hvem er den rigtige at fange, når det handler om hvordan I \
får hverdagen til at køre? … Er det [ejer]?"
  Kilde (GDPR): "Jeg har fundet jer i CVR-registeret og undersøgt lidt om, hvad \
I laver."
  Pitch: "Vi følger jeres virksomhed i 30 dage — ikke fysisk, remote — og ser \
helt konkret, hvor timerne og kronerne forsvinder. Derfra kigger vi på, hvad vi \
kan optimere i lige præcis de huller. [besparelses-sætning med DKK-spændet] \
Finder vi ikke noget, siger vi det til jer, og I betaler ikke en krone. Finder \
vi noget, betaler I først den første krone, når vi rent faktisk har bygget det \
til jer. Så med det sagt: Hvad er det hos jer, der æder tid, uden at det \
egentlig er dét, du er der for? … Og hvis du fik bare halvdelen af det tilbage \
— hvad ville du så bruge det på?"
  Pris: "Det er 100 % gratis at kigge. Finder vi noget, laver vi et estimat på, \
hvad det sparer jer — eller hvad det genererer i omsætning. Det kigger vi så på \
sammen, og først derefter bygger vi det. Og først når det er bygget, betaler I: \
20 % af det, vi rent faktisk har sparet jer i tid eller skabt i omsætning på et \
år — og det betaler I én gang."
  Book: "Skal vi ikke tage ti minutter, hvor jeg spørger ind til, hvordan I \
kører det i dag? Passer det bedst i morgen formiddag eller til eftermiddag?"

THE OFFER — READ CAREFULLY:
The caller does NOT sell websites, design, or marketing. The offer is this:
1. They follow the business remotely for 30 days — they look at how it actually \
runs day to day and find where the hours and the kroner disappear (manual admin, \
phone orders, quotes, planning, follow-up that never happens, double work).
2. They build the systems that close exactly those holes — automation, booking, \
follow-up, planning, reporting. Practical plumbing, not a software project the \
owner has to run.
3. Nothing is paid until it is built and working. Then the business pays \
**20% of one year's documented saving (or added revenue), ONCE** — measured \
against how things ran before. No fixed fee, no subscription, no binding. \
Nothing found or nothing saved = nothing paid. From year two the whole saving is \
theirs.
That risk-free structure IS the hook; the script already says it. Your job is \
to arm the caller with what is specific to THIS business.

THE ONE GOAL OF THIS CALL:
Book a short call/meeting (10–15 min) where the caller and the owner look \
together at where the time goes. Nothing else. Objection responses steer back \
to that booking — never to closing, scoping, or explaining technology.

THE MONEY — HANDLE HONESTLY:
The brief may contain "Realistisk årlig besparelse" — a DKK band plus the \
matching 20% fee. Read the "GRUNDLAG" line directly above it, because how the \
caller may talk about the number depends entirely on where it came from:
- GRUNDLAG: deres eget regnskab — the figures are the company's OWN published \
annual accounts (public via CVR). The caller may reference them out loud, and it \
is strong: "jeg kan se i jeres offentlige regnskab, at der ligger omkring X i \
drift under bruttofortjenesten — i virksomheder som jeres plejer der at være Y \
til Z af det i spildtid og dobbeltarbejde." Being open about reading their \
public accounts is disarming, not creepy. The saving itself is still an \
estimate — the accounts are fact, what we can remove is not.
- GRUNDLAG: brancheestimat — nothing usable was filed, so the number is an \
outside guess from sector and size. NEVER present it as their figure. Use it \
only as "hos virksomheder på jeres størrelse plejer der at ligge …".
In both cases: NEVER promise a specific saving, never say "vi sparer jer X". \
The fee is 20% of what is actually measured, paid once — that is what makes the \
number safe to talk about. If the brief says there is no figure at all, do NOT \
invent one.

NOT A WEBSITE PITCH:
The brief's "Teknisk modenhed" section is private background — it tells the \
caller how digital the business is and how technical to be. Never treat a \
missing or bad website as the problem. If the owner brings up their website, \
acknowledge it and steer back to where their time goes.

WHO ANSWERS THE PHONE:
The brief includes a "Telefonnummer-type" line. Mobilnummer: the OWNER most \
likely answers. Fastnet/hovednummer or 70/80-nummer: an employee or \
receptionist likely answers — include a gatekeeper objection in objections \
(e.g. "ejeren er her ikke" → get a name and the best time to call back, calmly).

VOICE for the objection responses — blend these, weighted toward the first:
- Jeremy Miner (NEPQ), dominant: calm, curious, low-pressure, relaxed and \
neutral tonality — never hyped. Soft, disarming questions; let THEM name what \
eats their time.
- Grant Cardone, a sprinkle: quiet, assumptive confidence; don't fold at the \
first "not interested" — stay warm and give one reason to stay curious.
- Alex Hormozi, a sprinkle: it is a no-brainer — nothing paid unless money is \
actually saved, and after the one-time 20% they keep everything.

You are given a factual brief about ONE business. Write in natural, spoken, \
professional Danish — the way a real person talks on the phone, not marketing \
copy.

Return JSON with these fields, all in Danish:
- summary_da: 1–2 sentences on who the business is and why they're a good fit to \
call right now (size, sector, what kind of manual load that usually means).
- weaknesses_da: the caller's PRIVATE notes — where the time and money most \
likely leak in this specific business (so the caller can recognise and probe \
what the owner names after the pain question), plus the savings math (estimated \
annual saving band, our one-time 20% share, what they keep). Bullet-ish and \
concrete. Never read aloud.
- objections: an array of the 2–3 MOST LIKELY objections for THIS specific \
lead, each with a short, calm, Miner-style response that de-escalates and steers \
back to booking. Pick what fits: "det er jeg ikke interesseret i", "vi har ikke \
tid", "hvordan kan I vide, hvad I kan spare os?", "vi har allerede styr på det", \
"send mig en mail", "hvad skal I bruge adgang til i de 30 dage?", or a \
gatekeeper. Do NOT include "hvad koster det?" — the script has a fixed answer. \
For scepticism about the number: agree openly that you don't know their business \
yet — that is exactly why the first step is to look, not to sell. Each item is \
{"objection_da": "...", "response_da": "..."}.
- competitor_name: a named competitor ONLY if one appears in the brief; otherwise "".
- competitor_angle_type: "fomo" if the notes lean on others in their trade \
already automating this, "first_mover" if they lean on being first locally to run \
things this way, or "none".

RULES: Ground every claim in the brief — never invent facts, numbers, awards, or \
competitor names. Never promise a specific saving. Never sell a website. You \
don't know the caller's or the firm's name — use a bracketed placeholder like \
[dit navn] or [firma] if you need it, and never invent a real company name. No \
emojis. Keep every objection response short and speakable."""

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


def _savings_block(savings: SavingsEstimate, employees: int | None) -> list[str]:
    """The heart of the brief: what we can realistically save, and our cut."""
    fee_pct = round(FEE_SHARE * 100)
    rate_pct = round(savings.rate * 100)

    if savings.from_accounts:
        lines = [
            "GRUNDLAG: deres eget regnskab (offentliggjort via CVR) — du må citere tallene",
            f"Bruttofortjeneste: {_dkk(savings.gross_profit or 0)} DKK",
        ]
        if savings.profit_loss is not None:
            lines.append(f"Årets resultat: {_dkk(savings.profit_loss)} DKK")
            lines.append(
                "Driftsomkostninger under bruttofortjenesten (løn, administration, drift): "
                f"ca. {_dkk(savings.pool)} DKK — det er den pulje, systemer kan spare af"
            )
        else:
            lines.append(
                f"Driftsomkostninger: ikke oplyst; vi regner på bruttofortjenesten "
                f"({_dkk(savings.pool)} DKK) som øvre grænse"
            )
        lines.append(
            f"Realistisk årlig besparelse (ca. {rate_pct}% af driftsomkostningerne): "
            f"{_dkk(savings.annual_low)}–{_dkk(savings.annual_high)} DKK om året "
            f"({savings.confidence} sikkerhed)"
        )
    else:
        lines = [
            "GRUNDLAG: brancheestimat — de har ikke offentliggjort brugbare regnskabstal "
            "(omsætning er ikke offentlig for regnskabsklasse B)",
        ]
        if savings.revenue:
            lines.append(f"Estimeret omsætning: ca. {_dkk(savings.revenue)} DKK (estimat)")
        lines.append(
            f"Realistisk årlig besparelse (ca. {rate_pct}% af omsætningen, "
            f"branchejusteret): {_dkk(savings.annual_low)}–{_dkk(savings.annual_high)} DKK "
            f"om året ({savings.confidence} sikkerhed)"
        )

    lines += [
        (
            f"Jeres honorar ({fee_pct}% af ét års faktisk besparelse, betalt én gang): "
            f"{_dkk(savings.fee_low)}–{_dkk(savings.fee_high)} DKK"
        ),
        (
            f"Virksomheden beholder selv: {_dkk(savings.keeps_low)}–"
            f"{_dkk(savings.keeps_high)} DKK det første år, og hele besparelsen derefter"
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
    if savings.from_accounts:
        lines.append(
            "VIGTIGT: regnskabstallene er fakta og må citeres — men BESPARELSEN er stadig "
            "et estimat af, hvad vi kan fjerne. Aldrig et løfte"
        )
    else:
        lines.append(
            "VIGTIGT: tallene er estimeret ud fra branche og størrelse — det er IKKE deres "
            "regnskab. Præsentér dem som et typisk spænd for virksomheder på deres "
            "størrelse, aldrig som deres tal og aldrig som et løfte"
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

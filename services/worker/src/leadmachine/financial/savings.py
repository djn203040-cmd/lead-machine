"""Realistic savings estimation — how much money the offer can actually free up.

The offer is performance-based: we follow the business for a period, build the
systems that remove its manual work, and take **20% of what we actually save
them**. So the number that matters on a cold call is no longer "what does a
website cost" but **"hvor meget kan vi realistisk spare jer om året?"**.

**We prefer their own filed accounts over any benchmark.** Under
årsregnskabsloven a regnskabsklasse B company — nearly every Danish SMB — may
publish *bruttofortjeneste* instead of *nettoomsætning*, so revenue is usually
not public (2 of 237 leads in the book disclose it) and has to be backed out of
a sector gross margin. But what they *do* file is exactly what we need:
bruttofortjeneste minus årets resultat is their **operating cost base** — the
wages, admin and overhead below the gross line, which is the only pool systems
can actually save from. So:

1. **accounts** — ``saving ≈ 10% × (gross_profit − profit_loss)``. Their numbers,
   quotable back to them on the call.
2. **benchmark** — only when nothing is filed: ``saving ≈ 10% of estimated
   revenue``, sector-adjusted downward where revenue is largely pass-through
   cost (a workshop's revenue is mostly parts; you cannot systematise away
   someone else's invoice) and capped against *bruttofortjeneste* if we have it.

Everything here is a defensible *estimate*, never a promise: the output is a
**band** (conservative → baseline) plus the confidence inherited from the
revenue estimate it rests on. The angle prompt is instructed to present it as a
typical range for a business this size, and the fee is charged on measured
savings only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .estimate import benchmark_for

# Our cut of what we actually save them. They keep the remaining 80%.
FEE_SHARE = 0.20

# Share of the *operating cost base* (bruttofortjeneste − årets resultat) that
# better systems can realistically remove. This is the preferred basis: it rests
# on figures the business actually filed, so the caller can quote them back.
OPERATING_SAVINGS_RATE = 0.10

# Fallback only, when nothing is filed: share of annual revenue a small Danish
# business can realistically claw back. 10% is the baseline; sectors where
# revenue is dominated by goods or vehicles get less, service sectors that are
# mostly time-and-admin get a little more.
DEFAULT_RATE = 0.10
SECTOR_RATE: dict[str, float] = {
    "food_drink": 0.10,
    "beauty_wellness": 0.12,
    "health": 0.12,
    "trades": 0.10,
    "cleaning": 0.10,
    "auto": 0.07,  # revenue is largely parts — not ours to save
    "transport": 0.07,  # fuel + vehicles dominate
    "retail": 0.06,  # varekøb dominates revenue
    "professional": 0.12,
    "finance": 0.12,
    "realestate": 0.10,
    "it_media": 0.10,
    "education": 0.10,
    "hospitality": 0.10,
    "leisure": 0.10,
    "business_services": 0.10,
}

# The conservative end of the band, as a share of the baseline estimate.
LOW_BAND = 0.6

# Benchmark path only: a sector estimate must not exceed a slice of the margin
# the business actually keeps. On the accounts path the cost base *is* reality,
# so nothing needs bounding against it.
GROSS_PROFIT_CAP = 0.30

# Nor more than the work there are people to do. Freeing ~a quarter of one
# employee's loaded cost, plus the waste and lost follow-up around them, tops
# out near this per head per year — beyond it the claim stops being sayable on
# a cold call.
MAX_PER_EMPLOYEE = 150_000

# Sanity ceiling — beyond this we are not the right partner anyway.
MAX_ANNUAL = 3_000_000

# Revenue-estimate method → how much we trust the number underneath.
_CONFIDENCE_DA: dict[str, str] = {
    "high": "høj",
    "medium": "middel",
    "low": "lav",
}

# The concrete, sector-typical places the time and money leak. These are the
# caller's *hypotheses* — things to ask about, never things to assert.
SECTOR_LEVERS: dict[str, tuple[str, ...]] = {
    "food_drink": (
        "bordbestilling og takeaway-ordrer, der tages i telefonen midt i driften",
        "vagtplanlægning og timeregistrering i hånden",
        "indkøb og madspild uden overblik over, hvad der faktisk sælges",
        "ingen automatisk opfølgning på gæster, der har været der én gang",
    ),
    "beauty_wellness": (
        "tidsbestilling, der tages over telefonen i stedet for online",
        "udeblivelser og sene afbud uden automatiske SMS-påmindelser",
        "ingen automatisk genbestilling til kunder, der plejer at komme hver 6.-8. uge",
        "tomme huller i kalenderen, der aldrig bliver fyldt ud",
    ),
    "health": (
        "tidsbestilling og ombookinger, der klares manuelt i telefonen",
        "udeblivelser uden automatiske påmindelser",
        "venteliste, der ikke automatisk fylder afbud ud",
        "journal- og attestadministration, der æder behandlingstid",
    ),
    "trades": (
        "tilbudsgivning, der tages om aftenen efter arbejdstid",
        "opfølgning på afgivne tilbud, der aldrig bliver ringet op igen",
        "timeregistrering og fakturering på papir eller i hovedet",
        "materialebestilling og kørselsplanlægning uden system",
    ),
    "cleaning": (
        "vagtplaner og afløsere, der koordineres via SMS",
        "timesedler, der samles ind og tastes manuelt",
        "kvalitetstjek og kundeklager uden fast opfølgning",
        "fakturering, der halter bagefter timerne",
    ),
    "auto": (
        "værkstedsbooking, der tages i telefonen midt i arbejdet",
        "tilbud og priser, der laves fra bunden hver gang",
        "ingen automatisk service-påmindelse til tidligere kunder",
        "reservedelsbestilling og lager uden overblik",
    ),
    "transport": (
        "ruteplanlægning og disponering i hånden",
        "fragtbreve og dokumentation på papir",
        "timeregistrering og kørselsafregning manuelt",
        "kundeopfølgning og faste ture uden automatik",
    ),
    "retail": (
        "lagerstyring og genbestilling på fornemmelse",
        "webshop- og butiksordrer, der ikke taler sammen",
        "ingen automatisk genkøbs-opfølgning til eksisterende kunder",
        "kampagner og tilbud, der laves manuelt hver gang",
    ),
    "professional": (
        "sagsstyring og dokumenter spredt over mail og drev",
        "timeregistrering, der rekonstrueres i slutningen af måneden",
        "fakturering og rykkere manuelt",
        "klientopfølgning og nye henvendelser uden fast proces",
    ),
    "finance": (
        "kundedokumentation og compliance-papirarbejde manuelt",
        "opfølgning på tilbud og fornyelser uden system",
        "rapportering, der samles i regneark hver måned",
    ),
    "realestate": (
        "fremvisninger og henvendelser koordineret i telefonen",
        "dokumenter og underskrifter frem og tilbage på mail",
        "ingen automatisk opfølgning på interesserede købere/lejere",
    ),
    "it_media": (
        "projekt- og opgavestyring spredt over værktøjer",
        "timeregistrering og fakturering manuelt",
        "tilbud og opfølgning uden fast proces",
    ),
    "education": (
        "tilmeldinger og betalinger håndteret manuelt",
        "holdplanlægning og aflysninger via mail",
        "ingen automatisk opfølgning på tidligere kursister",
    ),
    "hospitality": (
        "bookinger og forespørgsler besvaret manuelt",
        "vagtplaner og timeregistrering i hånden",
        "ingen automatisk opfølgning på gæster og gengangere",
    ),
    "leisure": (
        "medlems- og holdadministration manuelt",
        "betalinger og fornyelser, der skal rykkes for i hånden",
        "ingen automatisk opfølgning på frafaldne medlemmer",
    ),
    "business_services": (
        "vagt- og ressourceplanlægning i hånden",
        "timesedler og fakturering manuelt",
        "opfølgning på tilbud og forespørgsler uden system",
    ),
}

DEFAULT_LEVERS: tuple[str, ...] = (
    "administration og papirarbejde, der tages efter lukketid",
    "telefonbestillinger og forespørgsler, der afbryder driften",
    "opfølgning på tilbud og tidligere kunder, der ikke bliver til noget",
    "planlægning, timeregistrering og fakturering i hånden",
)


def group_for(branchekode: str | None) -> str | None:
    """Catalog group for a branchekode, or ``None`` when we can't place it.

    Reuses the revenue estimator's resolution (catalog → 2-digit division →
    default) so a lead's savings rate and its revenue benchmark never disagree
    about what sector it is in.
    """
    group = benchmark_for(branchekode).group
    return None if group == "default" else group


def savings_rate(branchekode: str | None) -> float:
    """Share of revenue realistically recoverable in this sector."""
    group = group_for(branchekode)
    return SECTOR_RATE.get(group or "", DEFAULT_RATE)


def levers_for(branchekode: str | None) -> tuple[str, ...]:
    """Sector-typical time/money leaks to ask about on the call."""
    group = group_for(branchekode)
    return SECTOR_LEVERS.get(group or "", DEFAULT_LEVERS)


def _round_dkk(value: float) -> int:
    """Round to a number a human would actually say out loud."""
    if value < 50_000:
        step = 1_000
    elif value < 200_000:
        step = 5_000
    elif value < 1_000_000:
        step = 10_000
    else:
        step = 50_000
    return int(round(value / step) * step)


@dataclass(frozen=True, slots=True)
class SavingsEstimate:
    """A defensible annual-savings band in DKK, plus our 20% cut of it."""

    annual_low: int
    annual_high: int
    fee_low: int
    fee_high: int
    keeps_low: int
    keeps_high: int
    rate: float
    confidence: str  # 'høj' | 'middel' | 'lav'
    # 'accounts' = derived from their filed figures (quotable back to them);
    # 'benchmark' = derived from an estimated revenue (nothing was filed).
    basis: str = "benchmark"
    # The pool the rate was applied to: operating cost base, or est. revenue.
    pool: int = 0
    revenue: int | None = None
    gross_profit: int | None = None
    profit_loss: int | None = None
    capped_by: str | None = None  # 'gross_profit' | 'headcount' | 'ceiling' | None

    @property
    def from_accounts(self) -> bool:
        return self.basis == "accounts"

    def as_dict(self) -> dict[str, Any]:
        return {
            "annual_low": self.annual_low,
            "annual_high": self.annual_high,
            "fee_low": self.fee_low,
            "fee_high": self.fee_high,
            "keeps_low": self.keeps_low,
            "keeps_high": self.keeps_high,
            "rate": self.rate,
            "basis": self.basis,
            "pool": self.pool,
            "revenue": self.revenue,
            "gross_profit": self.gross_profit,
            "profit_loss": self.profit_loss,
            "confidence": self.confidence,
            "capped_by": self.capped_by,
        }


def _number(value: Any) -> float | None:
    """A usable numeric value, or ``None`` (jsonb gives us whatever it gives us)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def estimate_savings(
    financial: dict[str, Any] | None,
    branchekode: str | None = None,
    employees: int | None = None,
) -> SavingsEstimate | None:
    """Annual savings we can realistically claim, from a lead's financial payload.

    ``financial`` is the ``lead_enrichment.financial`` jsonb (the filed figures +
    a revenue estimate); ``employees`` bounds the claim against the number of
    people there are to free up. Prefers their filed accounts and only falls
    back to a sector benchmark when nothing was filed. Returns ``None`` when
    there is neither — the caller then has no honest number to quote, and the
    prompt asks discovery questions instead of inventing one.
    """
    fin = financial or {}
    gross_profit = _number(fin.get("gross_profit"))
    profit_loss = _number(fin.get("profit_loss"))

    baseline: float | None = None
    basis = "benchmark"
    rate = OPERATING_SAVINGS_RATE
    pool = 0.0
    confidence = "lav"
    capped_by: str | None = None
    revenue: float | None = None

    # 1. Their own accounts. bruttofortjeneste − årets resultat is what they
    #    spend below the gross line: wages, admin, overhead. A loss makes the
    #    cost base *larger* than the gross profit, which is correct.
    if gross_profit is not None and gross_profit > 0:
        cost_base = gross_profit - profit_loss if profit_loss is not None else gross_profit
        if cost_base > 0:
            baseline = cost_base * OPERATING_SAVINGS_RATE
            basis = "accounts"
            pool = cost_base
            # Both figures filed → we know the cost base; only the gross profit
            # → we're using it as an upper bound on their operating costs.
            confidence = "høj" if profit_loss is not None else "middel"

    # 2. Nothing filed (or an unusable cost base): fall back to the sector rule.
    if baseline is None:
        estimate = fin.get("revenue_estimate") or {}
        revenue = _number(estimate.get("value"))
        if revenue is None or revenue <= 0:
            return None
        rate = savings_rate(branchekode)
        baseline = revenue * rate
        pool = revenue
        confidence = _CONFIDENCE_DA.get(str(estimate.get("confidence") or ""), "lav")
        # A benchmark must not out-claim the margin the business actually keeps.
        if gross_profit is not None:
            ceiling = gross_profit * GROSS_PROFIT_CAP
            if 0 < ceiling < baseline:
                baseline = ceiling
                capped_by = "gross_profit"

    # Caps that apply whatever the basis: only so many hands to free up, and a
    # sanity ceiling beyond which we are not the right partner anyway.
    if employees and employees > 0:
        ceiling = employees * MAX_PER_EMPLOYEE
        if ceiling < baseline:
            baseline = ceiling
            capped_by = "headcount"

    if baseline > MAX_ANNUAL:
        baseline = MAX_ANNUAL
        capped_by = "ceiling"

    high = _round_dkk(baseline)
    low = _round_dkk(baseline * LOW_BAND)
    if high <= 0:
        return None
    low = min(low, high)

    fee_low = _round_dkk(low * FEE_SHARE)
    fee_high = _round_dkk(high * FEE_SHARE)
    return SavingsEstimate(
        annual_low=low,
        annual_high=high,
        fee_low=fee_low,
        fee_high=fee_high,
        keeps_low=low - fee_low,
        keeps_high=high - fee_high,
        rate=rate,
        confidence=confidence,
        basis=basis,
        pool=round(pool),
        revenue=round(revenue) if revenue is not None else None,
        gross_profit=round(gross_profit) if gross_profit is not None else None,
        profit_loss=round(profit_loss) if profit_loss is not None else None,
        capped_by=capped_by,
    )

"""Robinson-list screening (M7 compliance gate)."""

from __future__ import annotations

from pathlib import Path

from leadmachine.compliance import (
    LeadToScreen,
    RobinsonList,
    normalize_name,
    robinson_key,
    run_robinson_screening,
)
from leadmachine.compliance.screen import SupabaseScreeningWriter

from .conftest import FakeSupabase


# --- normalization ---------------------------------------------------------
def test_normalize_strips_trade_prefix_and_case() -> None:
    assert normalize_name("v/Jens Hansen") == "jens hansen"
    assert normalize_name("Ved Mette Sørensen") == "mette sørensen"
    assert normalize_name("  JENS   HANSEN ") == "jens hansen"


def test_normalize_preserves_danish_letters_drops_accents() -> None:
    # æ/ø/å survive; a French accent is folded.
    assert normalize_name("Søren Bæk") == "søren bæk"
    assert normalize_name("Renée") == "renee"


def test_robinson_key_ignores_non_digit_postal() -> None:
    assert robinson_key("Jens Hansen", "DK-2200") == robinson_key("jens hansen", "2200")


# --- list membership -------------------------------------------------------
def test_contains_matches_on_name_and_postal() -> None:
    rl = RobinsonList.from_entries([("Jens Hansen", "2200")])
    assert rl.contains("v/Jens Hansen", "2200") is True
    assert rl.contains("Jens Hansen", "2100") is False  # different area
    assert rl.contains("Mette Hansen", "2200") is False  # different person


def test_empty_name_never_matches() -> None:
    rl = RobinsonList.from_entries([("", "2200")])
    assert rl.contains("", "2200") is False
    assert rl.is_empty is False  # the entry exists, it just can't be hit


def test_load_parses_jsonl_and_csv(tmp_path: Path) -> None:
    f = tmp_path / "robinson.txt"
    f.write_text(
        '# header comment\n'
        '{"name": "Jens Hansen", "postal_code": "2200"}\n'
        'Mette Sørensen;8000\n'
        '\n',
        encoding="utf-8",
    )
    rl = RobinsonList.load(f)
    assert len(rl) == 2
    assert rl.contains("Jens Hansen", "2200")
    assert rl.contains("Mette Sørensen", "8000")


def test_load_missing_path_is_empty() -> None:
    assert RobinsonList.load(None).is_empty
    assert RobinsonList.load("/no/such/file").is_empty


# --- screening job ---------------------------------------------------------
def _lead(lead_id: str, name: str, postal: str, sole: bool = True) -> LeadToScreen:
    return LeadToScreen(lead_id=lead_id, company_name=name, postal_code=postal, is_sole_trader=sole)


class FakeScreeningWriter:
    def __init__(self) -> None:
        self.marks: dict[str, tuple[bool, str | None]] = {}

    def mark(self, lead_id: str, *, suppressed: bool, reason: str | None) -> None:
        self.marks[lead_id] = (suppressed, reason)


def test_screening_suppresses_only_listed_sole_traders() -> None:
    rl = RobinsonList.from_entries([("Jens Hansen", "2200")])
    leads = [
        _lead("a", "Jens Hansen", "2200"),               # on the list -> suppressed
        _lead("b", "Mette Sørensen", "8000"),            # sole trader, not listed
        _lead("c", "Acme ApS", "2200", sole=False),      # limited company -> skipped
    ]
    writer = FakeScreeningWriter()
    stats = run_robinson_screening(leads, rl, writer)

    assert stats.seen == 3
    assert stats.sole_traders == 2
    assert stats.suppressed == 1
    assert stats.errors == 0
    assert writer.marks["a"] == (True, "robinson")
    assert writer.marks["b"] == (False, None)  # screened, recorded clean
    assert "c" not in writer.marks  # never screened


def test_supabase_writer_records_screened_at_and_suppression() -> None:
    fake = FakeSupabase()
    writer = SupabaseScreeningWriter(fake)
    writer.mark("lead-1", suppressed=True, reason="robinson")

    (table, row, _oc) = fake.log[-1]
    assert table == "leads"
    assert row["suppressed"] is True
    assert row["suppression_reason"] == "robinson"
    assert "robinson_screened_at" in row


def test_supabase_writer_clean_lead_only_stamps_screened_at() -> None:
    fake = FakeSupabase()
    SupabaseScreeningWriter(fake).mark("lead-2", suppressed=False, reason=None)
    (_table, row, _oc) = fake.log[-1]
    assert "robinson_screened_at" in row
    assert "suppressed" not in row  # a clean pass never flips the flag

"""Compliance enforcement (M7).

Discovery already suppresses ``reklamebeskyttelse`` + inactive entities at the
source. This package adds the second legal screen required before any outreach:
**Robinson-list screening for sole traders** (enkeltmandsvirksomhed / PMV), whose
contact data is personal data under GDPR.

See ``docs/compliance/`` for the LIA and the Art. 14 notices.
"""

from .robinson import RobinsonList, normalize_name, robinson_key
from .screen import (
    LeadToScreen,
    ScreeningStats,
    SupabaseScreeningWriter,
    run_robinson_screening,
)

__all__ = [
    "RobinsonList",
    "normalize_name",
    "robinson_key",
    "LeadToScreen",
    "ScreeningStats",
    "SupabaseScreeningWriter",
    "run_robinson_screening",
]

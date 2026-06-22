"""AI Danish sales angles (M6).

Generates a per-lead phone-call pitch with Claude — grounded in the lead's
website weaknesses and score breakdown — and writes it to ``lead_angles``.
Phone-first framing (Markedsføringsloven §10). The Claude client sits behind a
Protocol so the pipeline develops and tests with no API key or network.
"""

from __future__ import annotations

from .client import ANGLE_SCHEMA, ANGLES_MODEL, ClaudeAnglesClient
from .generate import (
    AnglesClientProtocol,
    AngleStats,
    AngleWriter,
    SupabaseAngleWriter,
    generate_one,
    run_angles,
)
from .models import Angle, LeadForAngle
from .prompt import build_prompt, build_user_prompt

__all__ = [
    "ClaudeAnglesClient",
    "ANGLES_MODEL",
    "ANGLE_SCHEMA",
    "build_prompt",
    "build_user_prompt",
    "generate_one",
    "run_angles",
    "AngleStats",
    "AnglesClientProtocol",
    "AngleWriter",
    "SupabaseAngleWriter",
    "Angle",
    "LeadForAngle",
]

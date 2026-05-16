"""Deterministic classification of Claude Code sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from crash_recovery.db import CLASSIFICATION_VALUES

CLASSIFIER_VERSION: int = 1
"""Bump when RULES changes shape. Scan re-classifies any row whose stored
classifier_version is below this constant. See design plan DR9."""


# Derived at module load from db.CLASSIFICATION_VALUES — single authoritative
# source for the schema-locked value set (see project CLAUDE.md, "Schema
# Constants from Authoritative Source"). Adding a value in db.py automatically
# extends this enum; removing one breaks any classify.py reference at import
# time. Members: LIVE, HARD_CRASH, BORDERLINE, CONCLUDED, IRRECOVERABLE.
ClassificationValue = StrEnum(
    "ClassificationValue",
    {v.upper(): v for v in CLASSIFICATION_VALUES},
)


@dataclass(frozen=True)
class Classification:
    value: ClassificationValue
    reason: str

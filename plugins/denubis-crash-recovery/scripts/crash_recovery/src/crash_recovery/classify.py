"""Deterministic classification of Claude Code sessions.

This module is a Functional Core: ``classify()`` is a pure function over the
inputs ``TailSummary`` (from :mod:`crash_recovery.jsonl`), :class:`LivenessState`
(from Phase 3's boot-aware liveness scan), and ``pid_alive`` (from Phase 3's
``kill -0`` probe). No I/O, no globals, no clock — given identical inputs the
output is bit-identical.

The :data:`RULES` tuple is the immutable, declarative classification table.
Each :class:`Rule` row has structured matcher fields; ``None`` is a wildcard
that matches any value of that input. ``classify()`` walks ``RULES`` in
declaration order and returns the first match — order is load-bearing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from crash_recovery.db import CLASSIFICATION_VALUES
from crash_recovery.jsonl import TailKind, TailSummary

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


@dataclass(frozen=True)
class LivenessState:
    """What ``classify()`` needs to know about the liveness signal.

    ``present`` is whether a liveness file exists for the session. When
    ``present`` is False, ``boot_id_current`` is meaningless (a wildcard for
    every rule that cares about boot-id).

    ``pid_alive`` is passed as a separate argument to ``classify()`` because
    it is conceptually orthogonal: ``None`` when no liveness file exists,
    otherwise the result of ``kill -0`` from Phase 3.
    """

    present: bool
    boot_id_current: bool


@dataclass(frozen=True)
class Rule:
    """One row of the classification table.

    Each matcher field is ``Optional``; ``None`` means "wildcard — match any
    value of this input". A rule fires when every non-None matcher field
    equals the corresponding input.
    """

    trailing_kind: Optional[TailKind]
    liveness_present: Optional[bool]
    pid_alive: Optional[bool]
    boot_id_current: Optional[bool]
    classification: ClassificationValue
    reason: str


# First-match semantics; reorder with care. Each row must be paired with a
# fixture in tests/test_classify.py (the parametrised test walks this tuple).
#
# Ordering rationale: failure modes that short-circuit the classifier
# (missing/malformed/empty JSONL) come first because they are independent of
# liveness state and any later rule's TailKind constraint would mask them.
# Boot-mismatch comes next because per design DR7 the boot-mismatch signal
# alone is sufficient evidence of a hard crash regardless of pid_alive or
# tail shape. The live/dead-pid family follows, ordered live-first so the
# happy path resolves quickly. The no-liveness family covers the remaining
# concluded/dangling tails. ``borderline_unknown_tail`` is the catch-all for
# UNKNOWN tails that fell through earlier liveness-specific rules.
RULES: tuple[Rule, ...] = (
    Rule(
        trailing_kind=TailKind.MISSING_FILE,
        liveness_present=None,
        pid_alive=None,
        boot_id_current=None,
        classification=ClassificationValue.IRRECOVERABLE,
        reason="missing_jsonl_on_disk",
    ),
    Rule(
        trailing_kind=TailKind.MALFORMED_TAIL,
        liveness_present=None,
        pid_alive=None,
        boot_id_current=None,
        classification=ClassificationValue.BORDERLINE,
        reason="malformed_tail",
    ),
    Rule(
        trailing_kind=TailKind.EMPTY,
        liveness_present=None,
        pid_alive=None,
        boot_id_current=None,
        classification=ClassificationValue.BORDERLINE,
        reason="empty_file",
    ),
    Rule(
        trailing_kind=None,
        liveness_present=True,
        pid_alive=None,
        boot_id_current=False,
        classification=ClassificationValue.HARD_CRASH,
        reason="liveness_boot_id_mismatch",
    ),
    Rule(
        trailing_kind=None,
        liveness_present=True,
        pid_alive=True,
        boot_id_current=True,
        classification=ClassificationValue.LIVE,
        reason="live_pid_present_boot_current",
    ),
    Rule(
        trailing_kind=TailKind.TOOL_USE_NO_RESULT,
        liveness_present=True,
        pid_alive=False,
        boot_id_current=True,
        classification=ClassificationValue.HARD_CRASH,
        reason="liveness_dead_pid_tool_use_no_result",
    ),
    Rule(
        trailing_kind=TailKind.ASK_QUESTION_NO_REPLY,
        liveness_present=True,
        pid_alive=False,
        boot_id_current=True,
        classification=ClassificationValue.HARD_CRASH,
        reason="liveness_dead_pid_ask_question_no_reply",
    ),
    Rule(
        trailing_kind=TailKind.AGENT_DISPATCH_NO_RESULT,
        liveness_present=True,
        pid_alive=False,
        boot_id_current=True,
        classification=ClassificationValue.HARD_CRASH,
        reason="liveness_dead_pid_agent_dispatch_no_result",
    ),
    Rule(
        trailing_kind=TailKind.UNKNOWN,
        liveness_present=True,
        pid_alive=False,
        boot_id_current=True,
        classification=ClassificationValue.HARD_CRASH,
        reason="liveness_dead_pid_unknown_tail",
    ),
    Rule(
        trailing_kind=TailKind.CONCLUDED,
        liveness_present=False,
        pid_alive=None,
        boot_id_current=None,
        classification=ClassificationValue.CONCLUDED,
        reason="no_liveness_clean_end_turn",
    ),
    Rule(
        trailing_kind=TailKind.TOOL_USE_NO_RESULT,
        liveness_present=False,
        pid_alive=None,
        boot_id_current=None,
        classification=ClassificationValue.BORDERLINE,
        reason="no_liveness_dangling_tool_use",
    ),
    Rule(
        trailing_kind=TailKind.ASK_QUESTION_NO_REPLY,
        liveness_present=False,
        pid_alive=None,
        boot_id_current=None,
        classification=ClassificationValue.BORDERLINE,
        reason="no_liveness_dangling_ask_question",
    ),
    Rule(
        trailing_kind=TailKind.AGENT_DISPATCH_NO_RESULT,
        liveness_present=False,
        pid_alive=None,
        boot_id_current=None,
        classification=ClassificationValue.BORDERLINE,
        reason="no_liveness_dangling_agent_dispatch",
    ),
    Rule(
        trailing_kind=TailKind.UNKNOWN,
        liveness_present=None,
        pid_alive=None,
        boot_id_current=None,
        classification=ClassificationValue.BORDERLINE,
        reason="unknown_tail_kind",
    ),
)


def classify(
    tail_summary: TailSummary,
    liveness_state: LivenessState,
    pid_alive: Optional[bool],
) -> Classification:
    """Return the first :class:`Classification` whose rule matches the inputs.

    Pure function: identical inputs produce identical outputs. The fallback
    ``Classification(BORDERLINE, "unmatched")`` is a deliberate review-queue
    route for realistic combinations the rules don't speak to (e.g., a
    concluded JSONL paired with a liveness file whose PID is dead but boot
    is still current — a scan/kill race). Phase 5's render surfaces it with
    a distinct "go look manually" message; Phase 7's triage skill tags such
    entries for review. AC3.3 (non-empty classification_reason) is preserved.

    Raises
    ------
    ValueError
        If ``liveness_state.present`` is ``True`` but ``pid_alive`` is
        ``None``. This is a contradictory caller input: a liveness file
        exists, so Phase 3 must have run ``kill -0`` and produced a concrete
        ``bool`` for ``pid_alive``. Receiving ``None`` here means the caller
        skipped the probe. Failing fast at the boundary is preferable to
        silently routing 4 distinct ``(TailKind, present=True, pid_alive=None,
        boot=True)`` combinations to the ``unmatched`` fallback. Resolved
        during Phase 2 review (2026-05-16).
    """
    # Boundary check: pid_alive=None means "no liveness file" per Phase 3's
    # caller contract. Passing it together with liveness_state.present=True
    # is contradictory — the file exists but the caller didn't run kill -0.
    # Fail fast at the boundary rather than silently routing 4 distinct
    # (kind, present=True, pid_alive=None, boot=True) combinations to
    # "unmatched". Resolved during Phase 2 review (2026-05-16).
    if liveness_state.present and pid_alive is None:
        raise ValueError(
            "liveness_state.present=True requires concrete pid_alive (bool); "
            "got None. Phase 3 caller must run kill -0 when a liveness file exists."
        )
    for rule in RULES:
        if rule.trailing_kind is not None and rule.trailing_kind is not tail_summary.kind:
            continue
        if rule.liveness_present is not None and rule.liveness_present is not liveness_state.present:
            continue
        if rule.pid_alive is not None and rule.pid_alive is not pid_alive:
            continue
        if rule.boot_id_current is not None and rule.boot_id_current is not liveness_state.boot_id_current:
            continue
        return Classification(value=rule.classification, reason=rule.reason)
    return Classification(value=ClassificationValue.BORDERLINE, reason="unmatched")

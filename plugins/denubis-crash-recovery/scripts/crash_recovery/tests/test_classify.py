"""Parametrised tests for the crash_recovery.classify rule table.

The parametrised ``test_every_rule_classifies_its_fixture`` walks every row
of ``RULES`` and asserts the rule fires for an input synthesised from its
matcher fields. This is the AC3.1 enforcement point (one assertion per row).

The standalone tests pin AC3.4 (malformed_tail), AC3.5 (empty_file), the
unmatched-route partition, the StrEnum return-type, the schema-source
convention, and unique reasons.
"""

from __future__ import annotations

import pytest

from crash_recovery.classify import (
    RULES,
    Classification,
    ClassificationValue,
    LivenessState,
    Rule,
    classify,
)
from crash_recovery.db import CLASSIFICATION_VALUES
from crash_recovery.jsonl import TailKind, TailSummary


def _build_tail_summary(kind: TailKind | None) -> TailSummary:
    """Synthesise a TailSummary whose kind matches the rule (or any kind if wildcard)."""
    use_kind = kind if kind is not None else TailKind.CONCLUDED
    return TailSummary(
        kind=use_kind,
        last_ts=0,
        total_entries=1,
        state_summary="synthetic-fixture",
    )


def _build_liveness_state(
    liveness_present: bool | None,
    boot_id_current: bool | None,
) -> LivenessState:
    """Synthesise a LivenessState matching the rule (or sane defaults if wildcard).

    When ``liveness_present`` is a wildcard we default to ``False`` — no
    liveness file. This avoids the classify() boundary check which requires a
    concrete ``pid_alive`` when ``present=True``: with ``present=False``,
    ``pid_alive=None`` is always valid. When ``boot_id_current`` is a wildcard
    we default to ``True``.
    """
    return LivenessState(
        present=liveness_present if liveness_present is not None else False,
        boot_id_current=boot_id_current if boot_id_current is not None else True,
    )


@pytest.mark.parametrize("rule", RULES, ids=lambda r: r.reason)
def test_every_rule_classifies_its_fixture(rule: Rule) -> None:
    """AC3.1 + AC3.3: every row of RULES fires for an input synthesised from its matchers."""
    tail = _build_tail_summary(rule.trailing_kind)
    liveness = _build_liveness_state(rule.liveness_present, rule.boot_id_current)

    # Resolve a concrete pid_alive for the test call that satisfies the
    # classify() boundary check (liveness_state.present=True requires a
    # concrete bool for pid_alive). When the rule's pid_alive is a wildcard
    # (None) but the effective liveness_present is True, supply False — a
    # concrete bool that the wildcard rule still matches.
    pid_alive = rule.pid_alive
    if pid_alive is None and liveness.present:
        pid_alive = False

    result = classify(tail, liveness, pid_alive=pid_alive)

    assert result.value == rule.classification, (
        f"rule {rule.reason!r} expected {rule.classification} but got {result.value}"
    )
    assert result.reason == rule.reason, (
        f"rule {rule.reason!r} matched but produced reason {result.reason!r}"
    )
    # AC3.3 explicit: classification_reason is non-empty.
    assert result.reason, "classification_reason must be non-empty"


def test_classify_is_idempotent() -> None:
    """Calling classify() twice with identical inputs returns equal Classifications."""
    tail = TailSummary(
        kind=TailKind.CONCLUDED,
        last_ts=0,
        total_entries=1,
        state_summary="x",
    )
    liveness = LivenessState(present=False, boot_id_current=False)

    first = classify(tail, liveness, pid_alive=None)
    second = classify(tail, liveness, pid_alive=None)

    assert first == second


def test_malformed_tail_maps_to_borderline_malformed_tail() -> None:
    """AC3.4: a malformed-tail JSONL must classify as borderline/malformed_tail."""
    tail = TailSummary(
        kind=TailKind.MALFORMED_TAIL,
        last_ts=None,
        total_entries=0,
        state_summary="malformed at tail",
    )
    liveness = LivenessState(present=False, boot_id_current=False)

    result = classify(tail, liveness, pid_alive=None)

    assert result == Classification(
        value=ClassificationValue.BORDERLINE, reason="malformed_tail"
    )


def test_empty_jsonl_maps_to_borderline_empty_file() -> None:
    """AC3.5: an empty JSONL must classify as borderline/empty_file."""
    tail = TailSummary(
        kind=TailKind.EMPTY,
        last_ts=None,
        total_entries=0,
        state_summary="empty jsonl",
    )
    liveness = LivenessState(present=False, boot_id_current=False)

    result = classify(tail, liveness, pid_alive=None)

    assert result == Classification(
        value=ClassificationValue.BORDERLINE, reason="empty_file"
    )


def test_unmatched_route_returns_borderline_unmatched() -> None:
    """Scan/kill race: concluded tail + dead pid on current boot is unmatched."""
    tail = TailSummary(
        kind=TailKind.CONCLUDED,
        last_ts=0,
        total_entries=1,
        state_summary="concluded",
    )
    liveness = LivenessState(present=True, boot_id_current=True)

    result = classify(tail, liveness, pid_alive=False)

    assert result.value == ClassificationValue.BORDERLINE
    assert result.reason == "unmatched"
    assert result.reason  # AC3.3 guard.


# Partition documentation: which input combinations are expected to route to
# `unmatched`, and which look like they might but are actually covered by a
# named rule. Adding a new RULES row that subsumes a positive case here MUST
# remove the entry from this list in the same commit.
_UNMATCHED_PARTITION_POSITIVE: tuple[tuple[TailKind, bool, bool, bool | None], ...] = (
    # (kind, liveness_present, boot_id_current, pid_alive)
    # Concluded JSONL but liveness file still records a dead PID on the
    # current boot — possible during scan/kill race conditions.
    (TailKind.CONCLUDED, True, True, False),
)

_UNMATCHED_PARTITION_NEGATIVE: tuple[
    tuple[TailKind, bool, bool, bool | None, str], ...
] = (
    # UNKNOWN + present liveness + dead pid + current boot is NOT unmatched;
    # it is covered by `liveness_dead_pid_unknown_tail`.
    (
        TailKind.UNKNOWN,
        True,
        True,
        False,
        "liveness_dead_pid_unknown_tail",
    ),
)


@pytest.mark.parametrize(
    "kind,liveness_present,boot_id_current,pid_alive",
    _UNMATCHED_PARTITION_POSITIVE,
)
def test_rules_table_partition_documents_unmatched_cases_positive(
    kind: TailKind,
    liveness_present: bool,
    boot_id_current: bool,
    pid_alive: bool | None,
) -> None:
    """Positive partition: each enumerated combination routes to unmatched."""
    tail = TailSummary(
        kind=kind, last_ts=0, total_entries=1, state_summary="partition"
    )
    liveness = LivenessState(
        present=liveness_present, boot_id_current=boot_id_current
    )

    result = classify(tail, liveness, pid_alive=pid_alive)

    assert result == Classification(
        value=ClassificationValue.BORDERLINE, reason="unmatched"
    )


@pytest.mark.parametrize(
    "kind,liveness_present,boot_id_current,pid_alive,expected_reason",
    _UNMATCHED_PARTITION_NEGATIVE,
)
def test_rules_table_partition_documents_unmatched_cases_negative(
    kind: TailKind,
    liveness_present: bool,
    boot_id_current: bool,
    pid_alive: bool | None,
    expected_reason: str,
) -> None:
    """Negative partition: combinations that look unmatched but are covered."""
    tail = TailSummary(
        kind=kind, last_ts=0, total_entries=1, state_summary="partition"
    )
    liveness = LivenessState(
        present=liveness_present, boot_id_current=boot_id_current
    )

    result = classify(tail, liveness, pid_alive=pid_alive)

    assert result.reason == expected_reason
    assert result.reason != "unmatched"


def test_classify_returns_classification_value_strenum() -> None:
    """classify() must return a ClassificationValue StrEnum, serialising as the documented string."""
    tail = TailSummary(
        kind=TailKind.CONCLUDED,
        last_ts=0,
        total_entries=1,
        state_summary="x",
    )
    liveness = LivenessState(present=False, boot_id_current=False)

    result = classify(tail, liveness, pid_alive=None)

    assert isinstance(result.value, ClassificationValue)
    # StrEnum members are strings; the value should equal the documented
    # column-string verbatim.
    assert result.value == "concluded"
    assert str(result.value) == "concluded"


def test_classification_value_matches_db_schema_source() -> None:
    """Pin: ClassificationValue is derived from db.CLASSIFICATION_VALUES.

    Catches future refactors that re-declare the enum literally and forget to
    keep it in lock-step with the CHECK-constraint value list. See project
    CLAUDE.md, "Schema Constants from Authoritative Source".
    """
    assert tuple(v.value for v in ClassificationValue) == CLASSIFICATION_VALUES


def test_rules_have_unique_reasons() -> None:
    """Every (classification, reason) pair in RULES must be unique."""
    pairs = [(r.classification, r.reason) for r in RULES]
    assert len(pairs) == len(set(pairs)), (
        f"duplicate (classification, reason) pairs in RULES: {pairs}"
    )


# Contradictory caller inputs: liveness_state.present=True but pid_alive=None.
# Phase 3 caller contract: when a liveness file exists, kill -0 MUST have run,
# producing a concrete bool. pid_alive=None means "no liveness file" — pairing
# it with present=True is a programming error. The boundary check in classify()
# must raise ValueError rather than silently routing to "unmatched".
_CONTRADICTORY_INPUTS: tuple[TailKind, ...] = (
    TailKind.CONCLUDED,
    TailKind.TOOL_USE_NO_RESULT,
    TailKind.ASK_QUESTION_NO_REPLY,
    TailKind.AGENT_DISPATCH_NO_RESULT,
)


@pytest.mark.parametrize("kind", _CONTRADICTORY_INPUTS, ids=lambda k: k.value)
def test_classify_rejects_contradictory_caller_inputs(kind: TailKind) -> None:
    """classify() raises ValueError for present=True + pid_alive=None (contradictory).

    Pins the structural boundary check added in Phase 2 review (Important finding).
    The 4 kinds above are the ones the review identified; each paired with
    present=True, pid_alive=None, boot_id_current=True covers the contradictory
    combinations that previously routed silently to "unmatched". A future
    refactor that drops the boundary check breaks this test immediately.
    """
    tail = TailSummary(
        kind=kind,
        last_ts=0,
        total_entries=1,
        state_summary="contradictory-input-test",
    )
    liveness = LivenessState(present=True, boot_id_current=True)

    with pytest.raises(ValueError) as exc_info:
        classify(tail, liveness, pid_alive=None)

    message = str(exc_info.value)
    assert "pid_alive" in message, (
        f"ValueError message must mention 'pid_alive'; got: {message!r}"
    )
    assert "liveness" in message, (
        f"ValueError message must mention 'liveness'; got: {message!r}"
    )

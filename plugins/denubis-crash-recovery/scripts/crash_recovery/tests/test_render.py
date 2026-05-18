"""Snapshot tests for :mod:`crash_recovery.render`.

Covers Phase 5 acceptance criteria:

* AC3.2 — byte-identical render across calls (snapshot tests + idempotency
  test).
* AC4.4 — direct edits to ``~/llm-resume.md`` do not persist (overwrite test).
* AC7.1 — concluded rows remain present after regenerate (no auto-pruning).

Plus the reason-prefix partition assertion that locks the three frozensets
(:data:`render.LIVENESS_REASONS`, :data:`render.NO_LIVENESS_REASONS`,
:data:`render.JSONL_ONLY_REASONS`) to every reason emitted by Phase 2's
``RULES`` plus the ``ambiguous_match`` (Phase 4 override) and ``unmatched``
(Phase 2 deliberate review-queue) routes.

The snapshot fixtures under ``tests/fixtures/snapshots/`` are byte-level
contracts: regenerating them auto-magically from the renderer defeats their
purpose. Each fixture was hand-authored against the entry template
documented in Phase 5 plan Task 2 and reviewed before commit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crash_recovery import render
from crash_recovery.classify import RULES, ClassificationValue
from crash_recovery.render import (
    JSONL_ONLY_REASONS,
    LIVENESS_REASONS,
    NO_LIVENESS_REASONS,
    SectionKey,
    _reduced_confidence_text,
    _section_for_row,
)

# Fixture import: pattern matches sibling test modules (test_scan,
# test_correlate) which import from ``fixtures`` rather than the
# fully-qualified ``crash_recovery.tests.fixtures``.
from fixtures.jsonl_builder import (
    DbFixtureRow,
    make_db_with_sessions,
)

SNAPSHOTS_DIR = Path(__file__).parent / "fixtures" / "snapshots"

# Deterministic epoch base used across all snapshot fixtures so two runs of
# the suite produce byte-identical render output (last_scanned drives ORDER
# BY but is never printed).
_BASE_EPOCH = 1_700_000_000


def _ts(index: int) -> int:
    """Return a deterministic epoch ``index`` minutes after ``_BASE_EPOCH``."""
    return _BASE_EPOCH + index * 60


# ---------------------------------------------------------------------------
# Snapshot fixtures (empty / mixed / all_concluded).
# ---------------------------------------------------------------------------


def _empty_sessions() -> list[DbFixtureRow]:
    """No rows — every section renders its empty_message."""
    return []


def _mixed_sessions() -> list[DbFixtureRow]:
    """One row per section, last_scanned descending by listed order.

    Section coverage (in render document order):

    * ``CURRENTLY_UNFINISHED`` — live row.
    * ``IDLE_LIVE_KILLED`` — hard_crash row.
    * ``AMBIGUOUS_CORRELATION`` — borderline / ambiguous_match.
    * ``NEEDS_INVESTIGATION`` — borderline / malformed_tail.
    * ``RECENTLY_CONCLUDED`` — concluded row carrying user_notes (exercises
      the Notes line in the entry template).
    * ``IRRECOVERABLE`` — irrecoverable / missing_jsonl_on_disk (exercises
      the strikethrough ``~~no resume — <reason>~~`` form).

    Ordering: the rows are listed in render document order with
    last_scanned values that DESCEND in that order, so each section's
    single row appears as the topmost-by-last_scanned within its section.
    """
    return [
        DbFixtureRow(
            uuid="aaaaaaaa-1111-1111-1111-111111111111",
            cwd="/work/live-project",
            classification="live",
            classification_reason="live_pid_present_boot_current",
            state_summary="tool_use in progress",
            user_notes=None,
            last_scanned=_ts(6),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="bbbbbbbb-2222-2222-2222-222222222222",
            cwd="/work/crashed-project",
            classification="hard_crash",
            classification_reason="liveness_boot_id_mismatch",
            state_summary="tool_use dangling at reboot",
            user_notes=None,
            last_scanned=_ts(5),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="cccccccc-3333-3333-3333-333333333333",
            cwd="/work/ambig-project",
            classification="borderline",
            classification_reason="ambiguous_match",
            state_summary="ambiguous match: 2 candidates",
            user_notes=None,
            last_scanned=_ts(4),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="dddddddd-4444-4444-4444-444444444444",
            cwd="/work/needs-look",
            classification="borderline",
            classification_reason="malformed_tail",
            state_summary="JSONL tail not valid JSON",
            user_notes=None,
            last_scanned=_ts(3),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="eeeeeeee-5555-5555-5555-555555555555",
            cwd="/work/done-project",
            classification="concluded",
            classification_reason="no_liveness_clean_end_turn",
            state_summary="end_turn observed",
            user_notes="follow up next week",
            last_scanned=_ts(2),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="ffffffff-6666-6666-6666-666666666666",
            cwd="/work/gone-project",
            classification="irrecoverable",
            classification_reason="missing_jsonl_on_disk",
            state_summary="JSONL deleted between scans",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
        ),
    ]


def _all_concluded_sessions() -> list[DbFixtureRow]:
    """Three concluded rows: one no-liveness, one liveness, one no-liveness again.

    Verifies that the reduced-confidence warning fires for the no-liveness
    rows and is omitted for the liveness row. Rows are ordered so the
    no-liveness rows bracket the liveness row in render output (by
    last_scanned DESC).
    """
    return [
        DbFixtureRow(
            uuid="11111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            cwd="/work/clean-finish-one",
            classification="concluded",
            classification_reason="no_liveness_clean_end_turn",
            state_summary="end_turn observed",
            user_notes=None,
            last_scanned=_ts(3),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="22222222-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            cwd="/work/clean-finish-with-liveness",
            classification="concluded",
            classification_reason="live_pid_present_boot_current",
            state_summary="end_turn observed",
            user_notes=None,
            last_scanned=_ts(2),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="33333333-cccc-cccc-cccc-cccccccccccc",
            cwd="/work/clean-finish-three",
            classification="concluded",
            classification_reason="no_liveness_clean_end_turn",
            state_summary="end_turn observed",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
        ),
    ]


_SNAPSHOT_CASES: dict[str, tuple[str, list[DbFixtureRow]]] = {
    "empty": ("expected_empty.md", _empty_sessions()),
    "mixed": ("expected_mixed.md", _mixed_sessions()),
    "all_concluded": ("expected_all_concluded.md", _all_concluded_sessions()),
}


@pytest.mark.parametrize("name", list(_SNAPSHOT_CASES.keys()))
def test_render_matches_snapshot(tmp_path: Path, name: str) -> None:
    """Render against each fixture and assert byte-equality with its snapshot.

    Snapshot files under ``tests/fixtures/snapshots/`` are byte-level
    contracts. Failures here mean either the renderer changed shape or the
    snapshot was edited by hand without reviewing the spec.
    """
    fixture_name, sessions = _SNAPSHOT_CASES[name]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)
    expected = (SNAPSHOTS_DIR / fixture_name).read_text(encoding="utf-8")
    assert actual == expected, (
        f"Snapshot mismatch for {name}.\n"
        f"--- expected ---\n{expected}\n"
        f"--- actual ---\n{actual}\n"
    )


def test_render_is_byte_identical_across_calls(tmp_path: Path) -> None:
    """AC3.2 idempotency: two render calls against the same DB return ``==``."""
    db_path = make_db_with_sessions(tmp_path, _mixed_sessions())
    first, _ = render.render(db_path)
    second, _ = render.render(db_path)
    assert first == second


def test_render_overwrites_user_edits(tmp_path: Path) -> None:
    """AC4.4: rendering to an existing file replaces it with DB-derived content.

    Writes a sentinel string to the output path, calls
    :func:`crash_recovery.__main__._render_to_file`, then reads the file
    back and asserts the sentinel is gone and the rendered preamble is
    present. Uses the CLI-layer helper because it exercises the
    tempfile+os.replace atomic-write path tested in Phase 5 Task 4.
    """
    from crash_recovery.__main__ import _render_to_file

    db_path = make_db_with_sessions(tmp_path, _mixed_sessions())
    output = tmp_path / "llm-resume.md"
    sentinel = "USER HAND-EDITED THIS FILE — DO NOT REMOVE"
    output.write_text(sentinel, encoding="utf-8")
    _render_to_file(db_path, output)
    actual = output.read_text(encoding="utf-8")
    assert sentinel not in actual
    assert "# Claude Code session resume" in actual


def test_regenerate_preserves_concluded_rows(tmp_path: Path) -> None:
    """AC7.1: concluded rows remain present in the rendered file after regenerate.

    Two concluded rows are seeded into the DB. The CLI render helper writes
    the file. Both concluded entries' uuid-short prefixes must appear in
    the rendered output (no auto-pruning side-effect).
    """
    from crash_recovery.__main__ import _render_to_file

    sessions = [
        DbFixtureRow(
            uuid="aaaaaaaa-cccc-cccc-cccc-cccccccccccc",
            cwd="/work/done-one",
            classification="concluded",
            classification_reason="no_liveness_clean_end_turn",
            state_summary="end_turn observed",
            user_notes=None,
            last_scanned=_ts(2),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="bbbbbbbb-cccc-cccc-cccc-cccccccccccc",
            cwd="/work/done-two",
            classification="concluded",
            classification_reason="no_liveness_clean_end_turn",
            state_summary="end_turn observed",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    output = tmp_path / "llm-resume.md"
    _render_to_file(db_path, output)
    actual = output.read_text(encoding="utf-8")
    assert "aaaaaaaa" in actual
    assert "bbbbbbbb" in actual
    # Both must live under the "Recently concluded" section header.
    assert "## Recently concluded" in actual


def test_reason_prefix_partition_is_exhaustive() -> None:
    """Every reason emitted by the classifier is in exactly one of three sets.

    Collects:

    * Every ``reason`` string from Phase 2's :data:`RULES`.
    * ``"ambiguous_match"`` — Phase 4's correlate-override reason.
    * ``"unmatched"`` — Phase 2's deliberate review-queue fallback in
      :func:`classify`.

    Asserts each reason belongs to exactly one of
    (:data:`LIVENESS_REASONS`, :data:`NO_LIVENESS_REASONS`,
    :data:`JSONL_ONLY_REASONS`). Without enumerating ``unmatched``
    explicitly, removing it from ``JSONL_ONLY_REASONS`` would not fail any
    test — defeats the partition guarantee.
    """
    reasons: set[str] = {rule.reason for rule in RULES}
    reasons.add("ambiguous_match")
    reasons.add("unmatched")

    for reason in sorted(reasons):
        memberships = [
            reason in LIVENESS_REASONS,
            reason in NO_LIVENESS_REASONS,
            reason in JSONL_ONLY_REASONS,
        ]
        assert sum(memberships) == 1, (
            f"reason {reason!r} must appear in exactly one of "
            f"(LIVENESS_REASONS, NO_LIVENESS_REASONS, JSONL_ONLY_REASONS); "
            f"memberships={memberships}"
        )

    # The three sets must also be pairwise disjoint (covers the case where
    # a future drift introduces a string into two sets without breaking
    # the per-reason loop above).
    assert LIVENESS_REASONS.isdisjoint(NO_LIVENESS_REASONS)
    assert LIVENESS_REASONS.isdisjoint(JSONL_ONLY_REASONS)
    assert NO_LIVENESS_REASONS.isdisjoint(JSONL_ONLY_REASONS)


def test_unmatched_reason_emits_review_queue_message(tmp_path: Path) -> None:
    """``unmatched`` → "Something fucky"; ``malformed_tail`` → generic warning.

    Locks the two-message split. ``unmatched`` routes through Phase 2's
    deliberate review-queue fallback and gets its own distinct prompt;
    every other JSONL-only reason gets the generic
    "session data is incomplete or corrupted" warning.
    """
    sessions = [
        DbFixtureRow(
            uuid="00000000-0000-0000-0000-000000000001",
            cwd="/work/unmatched",
            classification="borderline",
            classification_reason="unmatched",
            state_summary="rule table did not match",
            user_notes=None,
            last_scanned=_ts(2),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="00000000-0000-0000-0000-000000000002",
            cwd="/work/malformed",
            classification="borderline",
            classification_reason="malformed_tail",
            state_summary="JSONL tail not valid JSON",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)
    assert "⚠ Reduced confidence: Something fucky — let's go look" in actual
    assert (
        "⚠ Reduced confidence: session data is incomplete or corrupted"
        in actual
    )


def test_reduced_confidence_emitted_for_no_liveness_only(tmp_path: Path) -> None:
    """No-liveness rows get the warning; liveness rows do not."""
    sessions = [
        DbFixtureRow(
            uuid="00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            cwd="/work/no-liveness",
            classification="concluded",
            classification_reason="no_liveness_clean_end_turn",
            state_summary="end_turn observed",
            user_notes=None,
            last_scanned=_ts(2),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="00000000-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            cwd="/work/liveness",
            classification="live",
            classification_reason="live_pid_present_boot_current",
            state_summary="tool_use in progress",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)
    assert (
        "⚠ Reduced confidence: no liveness file recorded "
        "(pre-installation session or wrapper bypass)"
    ) in actual
    # The liveness row's uuid-short must appear, but its block must NOT
    # carry a reduced-confidence line. Walk the rendered text for that
    # block and verify.
    block_start = actual.index("00000000")  # first match: no-liveness row
    block_start = actual.index("00000000", block_start + 1)  # liveness row
    block = actual[block_start : block_start + 400]
    assert "Reduced confidence" not in block, block


# Hand-written independent source of truth for section assignment.
# Each entry is derived by applying _section_for_row's branching rules
# manually to every Phase 2 RULE:
#   "live"           → SectionKey.CURRENTLY_UNFINISHED
#   "hard_crash"     → SectionKey.IDLE_LIVE_KILLED
#   "concluded"      → SectionKey.RECENTLY_CONCLUDED
#   "irrecoverable"  → SectionKey.IRRECOVERABLE
#   "borderline" + reason=="ambiguous_match" → SectionKey.AMBIGUOUS_CORRELATION
#   "borderline" + anything else             → SectionKey.NEEDS_INVESTIGATION
#
# If a new RULE is added to classify.py without a corresponding entry here,
# the test will raise KeyError — loudly telling the author to update this dict.
_EXPECTED_SECTIONS: dict[tuple[str, str], SectionKey] = {
    # --- irrecoverable ---
    ("irrecoverable", "missing_jsonl_on_disk"): SectionKey.IRRECOVERABLE,
    # --- borderline (no liveness context) ---
    ("borderline", "malformed_tail"): SectionKey.NEEDS_INVESTIGATION,
    ("borderline", "empty_file"): SectionKey.NEEDS_INVESTIGATION,
    # --- hard_crash (liveness present, boot mismatch) ---
    ("hard_crash", "liveness_boot_id_mismatch"): SectionKey.IDLE_LIVE_KILLED,
    # --- live ---
    ("live", "live_pid_present_boot_current"): SectionKey.CURRENTLY_UNFINISHED,
    # --- hard_crash (liveness present, dead pid, boot current) ---
    ("hard_crash", "liveness_dead_pid_tool_use_no_result"): SectionKey.IDLE_LIVE_KILLED,
    ("hard_crash", "liveness_dead_pid_ask_question_no_reply"): SectionKey.IDLE_LIVE_KILLED,
    ("hard_crash", "liveness_dead_pid_agent_dispatch_no_result"): SectionKey.IDLE_LIVE_KILLED,
    ("hard_crash", "liveness_dead_pid_unknown_tail"): SectionKey.IDLE_LIVE_KILLED,
    # --- concluded ---
    ("concluded", "no_liveness_clean_end_turn"): SectionKey.RECENTLY_CONCLUDED,
    # --- borderline (no liveness, dangling tails) ---
    ("borderline", "no_liveness_dangling_tool_use"): SectionKey.NEEDS_INVESTIGATION,
    ("borderline", "no_liveness_dangling_ask_question"): SectionKey.NEEDS_INVESTIGATION,
    ("borderline", "no_liveness_dangling_agent_dispatch"): SectionKey.NEEDS_INVESTIGATION,
    # --- borderline (unknown tail, catch-all) ---
    ("borderline", "unknown_tail_kind"): SectionKey.NEEDS_INVESTIGATION,
}


@pytest.mark.parametrize(
    ("classification", "reason"),
    [
        (rule.classification.value, rule.reason)
        for rule in RULES
    ],
)
def test_section_assignment_for_every_phase_2_reason(
    classification: str, reason: str
) -> None:
    """Asserts that ``_section_for_row`` returns the documented SectionKey for every Phase 2 RULE.

    The expected mapping is hand-written in ``_EXPECTED_SECTIONS`` as an
    independent source of truth. If ``_section_for_row`` ever disagrees with
    the expected mapping, the test fails. If a new RULE is added to
    :data:`classify.RULES` without a corresponding entry in
    ``_EXPECTED_SECTIONS``, the test raises ``KeyError`` — loudly telling the
    author to update the dict.
    """
    expected = _EXPECTED_SECTIONS[(classification, reason)]
    assert _section_for_row(classification, reason) is expected


def test_irrecoverable_row_suppresses_resume_command(tmp_path: Path) -> None:
    """Irrecoverable rows render strikethrough markers, no ``claudew --resume``.

    Covers both irrecoverable reasons:

    * ``missing_jsonl_on_disk`` — Phase 2 outcome when the JSONL was
      deleted between scans.
    * ``missing_cwd`` — Phase 4 M3 outcome (cwd is empty so a resume
      would land in the wrong working directory).

    For each row the rendered entry must contain the strikethrough resume
    marker (``~~no resume — <reason>~~``) and MUST NOT contain the
    ``claudew --resume`` substring. The other three template lines
    (Working dir, Classification, State) must still appear.

    Locks the Phase 4 coherence-review falsification anchor (2026-05-17):
    irrecoverable rows do not advertise a resume command.
    """
    sessions = [
        DbFixtureRow(
            uuid="aaaaaaaa-9999-9999-9999-999999999991",
            cwd="/work/gone-on-disk",
            classification="irrecoverable",
            classification_reason="missing_jsonl_on_disk",
            state_summary="JSONL deleted between scans",
            user_notes=None,
            last_scanned=_ts(2),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="bbbbbbbb-9999-9999-9999-999999999992",
            cwd="",
            classification="irrecoverable",
            classification_reason="missing_cwd",
            state_summary="liveness file present without cwd",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)

    assert "~~no resume — missing_jsonl_on_disk~~" in actual
    assert "~~no resume — missing_cwd~~" in actual
    assert "claudew --resume" not in actual, (
        "Irrecoverable rows must not advertise claudew --resume; "
        f"got rendered output containing it:\n{actual}"
    )

    # Verify the other template lines still appear in each entry.
    assert "  - Working dir: `/work/gone-on-disk`" in actual
    assert "  - Working dir: ``" in actual  # missing_cwd row
    assert "  - Classification: `irrecoverable` (`missing_jsonl_on_disk`)" in actual
    assert "  - Classification: `irrecoverable` (`missing_cwd`)" in actual
    assert "  - State: JSONL deleted between scans" in actual
    assert "  - State: liveness file present without cwd" in actual

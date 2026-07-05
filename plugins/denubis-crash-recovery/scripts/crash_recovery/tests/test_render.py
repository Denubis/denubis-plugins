"""Snapshot and acceptance-criteria tests for :mod:`crash_recovery.render`.

Covers Phase 4/5 acceptance criteria:

* AC1.2 — hard_crash rows render under ``## Probable system-crash victims``
  with their full UUID and a ``claudew --resume <full-uuid>`` line.
* AC5.1 — every in-scope session renders; the crash highlight adds a section,
  never drops a roster row.
* AC5.2 — the resume line carries the full UUID; pane-title, last-substantive,
  and last-activity render when present; the styled 8-char form is suppressed
  when a pane_title is available.
* AC5.3 / AC3.2 — byte-identical render across calls (snapshot + idempotency).
* AC7.3 — render on a not-yet-migrated DB (missing the Phase-4 columns) does
  not raise ``OperationalError``; the new fields render as absent.
* AC4.4 — direct edits to ``~/llm-resume.md`` do not persist (overwrite test).
* AC7.1 — concluded rows remain present after regenerate (no auto-pruning).

Plus the reason-prefix partition assertion that locks the three frozensets
(:data:`render.LIVENESS_REASONS`, :data:`render.NO_LIVENESS_REASONS`,
:data:`render.JSONL_ONLY_REASONS`) to every reason emitted by Phase 2's
``RULES`` plus the ``ambiguous_match`` (Phase 4 override) and ``unmatched``
(Phase 2 deliberate review-queue) routes.

The snapshot fixtures under ``tests/fixtures/snapshots/`` are determinism and
regression locks, not the AC teeth. They are regenerated to match the renderer
output, so a snapshot match alone proves only that two runs are byte-identical
(AC5.3) — never that the output is *correct*. Correctness is verified by the
independent per-AC assertions below (``test_crash_victims_*``,
``test_all_means_all_*``, ``test_full_uuid_*``, ``test_render_old_shape_db_*``),
each of which checks a specific behaviour without reference to the snapshots.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from crash_recovery import render
from crash_recovery.classify import RULES
from crash_recovery.render import (
    JSONL_ONLY_REASONS,
    LIVENESS_REASONS,
    NO_LIVENESS_REASONS,
    SectionKey,
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
    * ``PROBABLE_CRASH_VICTIMS`` — hard_crash row.
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
    assert "⚠ Reduced confidence: session data is incomplete or corrupted" in actual


def test_concluded_dead_pid_emits_calm_label_not_something_fucky(
    tmp_path: Path,
) -> None:
    """A ``liveness_dead_pid_concluded_tail`` row renders a calm, specific
    explanation and NOT the alarming ``unmatched`` "Something fucky" net.

    This is the "finished a turn, then the process was killed" case. It lands in
    Needs investigation (borderline), is findable by its reason, and carries a
    plain-language note that it is likely nothing to resume — the calm label that
    replaces the generic review-queue prompt.
    """
    sessions = [
        DbFixtureRow(
            uuid="00000000-0000-0000-0000-0000000c0c0c",
            cwd="/work/concluded-killed",
            classification="borderline",
            classification_reason="liveness_dead_pid_concluded_tail",
            state_summary="concluded - end_turn",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)
    entry = _section_body(actual, "## Needs investigation")
    assert "liveness_dead_pid_concluded_tail" in entry  # findable by reason
    assert "Something fucky" not in entry
    # Calm, specific explanation present.
    assert "concluded, then" in entry
    assert "killed" in entry


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
#   "hard_crash"     → SectionKey.PROBABLE_CRASH_VICTIMS
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
    ("hard_crash", "liveness_boot_id_mismatch"): SectionKey.PROBABLE_CRASH_VICTIMS,
    # --- live ---
    ("live", "live_pid_present_boot_current"): SectionKey.CURRENTLY_UNFINISHED,
    # --- hard_crash (liveness present, dead pid, boot current) ---
    (
        "hard_crash",
        "liveness_dead_pid_tool_use_no_result",
    ): SectionKey.PROBABLE_CRASH_VICTIMS,
    (
        "hard_crash",
        "liveness_dead_pid_ask_question_no_reply",
    ): SectionKey.PROBABLE_CRASH_VICTIMS,
    (
        "hard_crash",
        "liveness_dead_pid_agent_dispatch_no_result",
    ): SectionKey.PROBABLE_CRASH_VICTIMS,
    ("hard_crash", "liveness_dead_pid_unknown_tail"): SectionKey.PROBABLE_CRASH_VICTIMS,
    # --- concluded ---
    ("concluded", "no_liveness_clean_end_turn"): SectionKey.RECENTLY_CONCLUDED,
    # --- borderline (no liveness, dangling tails) ---
    ("borderline", "no_liveness_dangling_tool_use"): SectionKey.NEEDS_INVESTIGATION,
    ("borderline", "no_liveness_dangling_ask_question"): SectionKey.NEEDS_INVESTIGATION,
    (
        "borderline",
        "no_liveness_dangling_agent_dispatch",
    ): SectionKey.NEEDS_INVESTIGATION,
    # --- borderline (unknown tail, catch-all) ---
    ("borderline", "unknown_tail_kind"): SectionKey.NEEDS_INVESTIGATION,
    # --- borderline (liveness present, dead pid, concluded tail) ---
    ("borderline", "liveness_dead_pid_concluded_tail"): SectionKey.NEEDS_INVESTIGATION,
}


@pytest.mark.parametrize(
    ("classification", "reason"),
    [(rule.classification.value, rule.reason) for rule in RULES],
)
def test_section_assignment_for_every_phase_2_reason(
    classification: str, reason: str
) -> None:
    """Asserts that ``_section_for_row`` returns the documented SectionKey
    for every Phase 2 RULE.

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


# ---------------------------------------------------------------------------
# Phase 4 acceptance criteria (crash-victims top section, full UUID, new
# fields, graceful degradation on an un-migrated DB). These are the AC teeth:
# each asserts a specific behaviour without reference to the snapshots.
# ---------------------------------------------------------------------------


def _section_body(rendered: str, header: str) -> str:
    """Return the slice of ``rendered`` from ``header`` to the next ``## `` header.

    Lets a test scope substring assertions to a single section's body rather
    than the whole document. ``header`` must be a full section header line
    (e.g. ``"## Probable system-crash victims"``).
    """
    start = rendered.index(header)
    rest = rendered[start + len(header) :]
    next_header = rest.find("\n## ")
    return rest if next_header == -1 else rest[:next_header]


def test_crash_victims_render_in_top_section_with_full_uuid(tmp_path: Path) -> None:
    """AC1.2: a hard_crash row lands under ``## Probable system-crash victims``.

    The section header is the FIRST one in the document (top section), the
    entry carries the FULL uuid, and the body advertises
    ``claudew --resume <full-uuid>``.
    """
    full_uuid = "abcdef01-2222-3333-4444-555566667777"
    sessions = [
        DbFixtureRow(
            uuid=full_uuid,
            cwd="/work/crashed",
            classification="hard_crash",
            classification_reason="liveness_boot_id_mismatch",
            state_summary="tool_use dangling at reboot",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)

    crash_header = "## Probable system-crash victims"
    assert crash_header in actual
    # Top section: the crash header precedes every other section header.
    assert actual.index(crash_header) < actual.index("## Currently unfinished")
    # The old section header is gone entirely.
    assert "## Idle-live killed" not in actual

    body = _section_body(actual, crash_header)
    assert full_uuid in body
    assert f"claudew --resume {full_uuid}" in body


def test_all_means_all_every_classification_renders_once(tmp_path: Path) -> None:
    """AC5.1: one row per classification → every row renders, crash section added.

    All-means-all is a section, never a filter: the crash highlight adds a
    section AND the other five sections stay populated. Each row gets a
    DISTINCT cwd (no substrings of each other) so the per-row
    ``Working dir`` line is an unambiguous once-each presence check that works
    even for the irrecoverable row (which emits no full-uuid resume line).
    """
    rows = [
        ("live", "live_pid_present_boot_current", "/w/alpha"),
        ("hard_crash", "liveness_boot_id_mismatch", "/w/bravo"),
        ("borderline", "ambiguous_match", "/w/charlie"),
        ("borderline", "unknown_tail_kind", "/w/delta"),
        ("concluded", "no_liveness_clean_end_turn", "/w/echo"),
        ("irrecoverable", "missing_jsonl_on_disk", "/w/foxtrot"),
    ]
    sessions = [
        DbFixtureRow(
            uuid=f"{i}0000000-0000-0000-0000-00000000000{i}",
            cwd=cwd,
            classification=classification,
            classification_reason=reason,
            state_summary=f"state for {cwd}",
            user_notes=None,
            last_scanned=_ts(len(rows) - i),
            first_seen=_ts(0),
        )
        for i, (classification, reason, cwd) in enumerate(rows)
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)

    # Every row renders exactly once. Count the per-row Working-dir line —
    # the one line every classification emits, irrecoverable included.
    for _classification, _reason, cwd in rows:
        line = f"  - Working dir: `{cwd}`"
        assert actual.count(line) == 1, f"{cwd}: count={actual.count(line)}"

    # Crash section present AND first; all five other sections still present.
    crash_header = "## Probable system-crash victims"
    assert actual.index(crash_header) < actual.index("## Currently unfinished")
    for header in (
        "## Currently unfinished",
        "## Ambiguous correlation",
        "## Needs investigation",
        "## Recently concluded",
        "## Irrecoverable",
    ):
        assert header in actual

    # The crash row sits under the crash header, not elsewhere.
    crash_body = _section_body(actual, crash_header)
    assert "  - Working dir: `/w/bravo`" in crash_body


def test_full_uuid_present_styled_short_form_absent(tmp_path: Path) -> None:
    """AC5.2: a row with pane_title + last_substantive + jsonl_last_ts.

    All three new fields render. The resume line carries the FULL uuid, the
    bold label is the human-meaningful pane_title, and the *styled* 8-char
    forms (``**<hash>**`` and ``(session <hash>)``) are absent. The raw
    8-char prefix is necessarily a substring of the full uuid, so asserting
    its bare absence would be a false trap — only the styled forms must go.
    """
    full_uuid = "deadbeef-1111-2222-3333-444455556666"
    short = full_uuid[:8]
    pane_title = "my-tmux-window"  # contains no hex hash
    last_substantive = "Implemented the parser fix"
    last_ts = 1_700_000_500
    sessions = [
        DbFixtureRow(
            uuid=full_uuid,
            cwd="/work/proj",
            classification="hard_crash",
            classification_reason="liveness_boot_id_mismatch",
            state_summary="tool_use dangling at reboot",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
            jsonl_last_ts=last_ts,
            pane_title=pane_title,
            last_substantive=last_substantive,
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)

    entry = _section_body(actual, "## Probable system-crash victims")

    # Full uuid present in the resume line.
    assert f"claudew --resume {full_uuid}" in entry
    # The bold label is the pane_title, not a hash.
    assert f"**{pane_title}**" in entry
    # Both new fields render.
    assert f"  - Last substantive: {last_substantive}" in entry
    from datetime import datetime

    expected_iso = datetime.fromtimestamp(last_ts, tz=UTC).isoformat()
    assert f"  - Last activity: {expected_iso}" in entry
    # The styled 8-char forms must NOT appear. (Bare `short in entry` is True
    # via the full uuid and is therefore not a valid assertion.)
    assert f"**{short}**" not in entry
    assert f"(session {short})" not in entry


def test_render_single_lines_stored_multiline_last_substantive(
    tmp_path: Path,
) -> None:
    """Defensive: a row stored before the extraction fix renders on one line.

    Rows written before the ``jsonl.last_substantive_text`` newline-collapse fix
    carry embedded newlines in ``last_substantive``. Render must single-line the
    stored value itself — otherwise an embedded ``## heading`` lands at column 0,
    is parsed as a new report section, and shreds the structure. Without this,
    those rows stay unreadable until a full re-scan overwrites them.
    """
    full_uuid = "abad1dea-1111-2222-3333-444455556666"
    # Heading is NOT first, so it leaks to column 0 of a following line when the
    # stored newlines survive — the exact real-DB shredding pattern.
    dirty = "Implemented the fix.\n## What changed\n- pulled new bib\n"
    sessions = [
        DbFixtureRow(
            uuid=full_uuid,
            cwd="/work/dirty",
            classification="hard_crash",
            classification_reason="liveness_boot_id_mismatch",
            state_summary="tool_use dangling at reboot",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
            jsonl_last_ts=1_700_000_500,
            pane_title=None,
            last_substantive=dirty,
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)
    lines = actual.splitlines()

    # No rendered line is a column-0 markdown heading leaked from the field.
    leaked = [ln for ln in lines if ln.startswith("## What changed")]
    assert leaked == [], f"leaked column-0 heading from last_substantive: {leaked!r}"
    # The whole snippet sits on exactly one collapsed "Last substantive" line.
    subst = [ln for ln in lines if ln.startswith("  - Last substantive:")]
    assert len(subst) == 1
    assert "Implemented the fix." in subst[0]
    assert "## What changed" in subst[0]
    assert "pulled new bib" in subst[0]


def test_header_label_falls_back_to_last_substantive(tmp_path: Path) -> None:
    """AC5.2 (middle branch): no pane_title but last_substantive present.

    A jsonl-only session has ``pane_title=None`` (no snapshot anchor) yet may
    carry a ``last_substantive`` snippet. The bold label is then that snippet,
    NOT the last-resort ``(session <hash>)`` parenthetical, and the full uuid
    still drives the resume line.
    """
    full_uuid = "feedface-1111-2222-3333-444455556666"
    short = full_uuid[:8]
    snippet = "Refactored the correlate window filter"
    sessions = [
        DbFixtureRow(
            uuid=full_uuid,
            cwd="/work/jsonl-only",
            classification="borderline",
            classification_reason="unknown_tail_kind",
            state_summary="tail kind not recognised",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
            pane_title=None,
            last_substantive=snippet,
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)
    entry = _section_body(actual, "## Needs investigation")
    assert f"**{snippet}**" in entry
    assert f"(session {short})" not in entry
    assert f"claudew --resume {full_uuid}" in entry


def test_last_activity_line_omitted_when_jsonl_last_ts_none(tmp_path: Path) -> None:
    """AC5.2 (None branch): a row with ``jsonl_last_ts=None`` omits Last activity.

    The default fixture rows all carry a non-None ``jsonl_last_ts``, so the
    omit-when-None branch is otherwise unexercised.
    """
    sessions = [
        DbFixtureRow(
            uuid="00000000-dead-dead-dead-000000000000",
            cwd="/work/no-ts",
            classification="hard_crash",
            classification_reason="liveness_boot_id_mismatch",
            state_summary="no activity timestamp",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
            jsonl_last_ts=None,
        ),
    ]
    db_path = make_db_with_sessions(tmp_path, sessions)
    actual, _ = render.render(db_path)
    assert "Last activity:" not in actual


def test_render_old_shape_db_does_not_raise(tmp_path: Path) -> None:
    """AC7.3: render on a not-yet-migrated DB does not raise ``OperationalError``.

    Build a pre-Phase-4 ``sessions`` table by DIRECT SQL (without the
    ``pane_title``/``last_substantive`` columns), bypassing ``init()`` (which
    runs ``_migrate_additive_columns`` and would add the columns) and
    ``open_db()`` (which refuses an un-migrated DB with RuntimeError).
    ``render()`` opens its own read-only connection, never migrates, and never
    calls ``open_db()``, so it must tolerate the old shape. ``jsonl_last_ts`` is
    pre-Phase-4 (db.py:51) and stays present.
    """
    import sqlite3

    db_path = tmp_path / "old-shape.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            """
            CREATE TABLE sessions (
                uuid                  TEXT PRIMARY KEY NOT NULL,
                project_path          TEXT NOT NULL,
                cwd                   TEXT NOT NULL,
                jsonl_path            TEXT,
                jsonl_mtime           INTEGER,
                jsonl_last_ts         INTEGER,
                classification        TEXT NOT NULL,
                classification_reason TEXT,
                classifier_version    INTEGER NOT NULL,
                state_summary         TEXT,
                first_seen            INTEGER NOT NULL,
                last_scanned          INTEGER NOT NULL,
                user_notes            TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO sessions (
                uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                classification, classification_reason, classifier_version,
                state_summary, first_seen, last_scanned, user_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "11111111-old0-old0-old0-111111111111",
                "/decoded/project",
                "/work/old-shape",
                "/jsonl/old.jsonl",
                1_700_000_000,
                1_700_000_000,
                "hard_crash",
                "liveness_boot_id_mismatch",
                1,
                "old-shape state",
                _ts(0),
                _ts(1),
                None,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Must not raise OperationalError ("no such column: pane_title").
    actual, count = render.render(db_path)
    assert count == 1
    # The old-shape row still renders (under the crash section), with the new
    # fields treated as absent (no Last substantive line).
    assert "/work/old-shape" in actual
    assert "Last substantive:" not in actual
    assert "## Probable system-crash victims" in actual


def _insert_uncorrelated_marker(
    db_path: Path,
    *,
    boot_id: str,
    pid: int,
    cwd: str,
    started: int | None,
    reason: str,
    last_scanned: int,
) -> None:
    """Insert one row into ``uncorrelated_markers`` (the render-only data source)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO uncorrelated_markers "
            "(boot_id, pid, cwd, started, reason, last_scanned) VALUES (?,?,?,?,?,?)",
            (boot_id, pid, cwd, started, reason, last_scanned),
        )
        conn.commit()
    finally:
        conn.close()


def test_render_surfaces_uncorrelated_markers_section(tmp_path: Path) -> None:
    """An uncorrelated abnormal-exit marker renders its own section with cwd,
    started time, and reason — surfaced rather than silently dropped (Gap A).

    Markers are not sessions, so the row count stays at the number of session
    rows (here 0); the marker lives in a supplementary section.
    """
    db_path = make_db_with_sessions(tmp_path, [])
    started = 1_781_682_073
    _insert_uncorrelated_marker(
        db_path,
        boot_id="85c5ebd8-12c1-4200-915a-d29845a0667e",
        pid=663495,
        cwd="/work/bjet-phase1",
        started=started,
        reason="dead_pid",
        last_scanned=1_781_900_000,
    )
    actual, count = render.render(db_path)

    assert "## Uncorrelated crash markers" in actual
    section = _section_body(actual, "## Uncorrelated crash markers")
    assert "663495" in section
    assert "/work/bjet-phase1" in section
    expected_iso = datetime.fromtimestamp(started, tz=UTC).isoformat()
    assert expected_iso in section
    # Markers are not sessions: the row count is unaffected.
    assert count == 0
    # No resume command — there is nothing to resume.
    assert "claudew --resume" not in section


def test_render_omits_uncorrelated_section_when_empty(tmp_path: Path) -> None:
    """With no uncorrelated markers, the section is omitted entirely (not an empty
    header). It is supplementary evidence, shown only when present — so existing
    reports are unchanged when there is nothing to surface.
    """
    db_path = make_db_with_sessions(tmp_path, [])
    actual, _ = render.render(db_path)
    assert "Uncorrelated crash markers" not in actual


def _lean_fixture_sessions() -> list[DbFixtureRow]:
    """Five rows: a crash victim + a dangling signal (actionable), and one each of
    concluded / irrecoverable / unknown_tail_kind (bulk, collapsed in lean mode)."""
    return [
        DbFixtureRow(
            uuid="aaaaaaaa-0000-0000-0000-000000000001",
            cwd="/work/crash",
            classification="hard_crash",
            classification_reason="liveness_boot_id_mismatch",
            state_summary="boom",
            user_notes=None,
            last_scanned=_ts(5),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="bbbbbbbb-0000-0000-0000-000000000002",
            cwd="/work/done",
            classification="concluded",
            classification_reason="no_liveness_clean_end_turn",
            state_summary="done",
            user_notes=None,
            last_scanned=_ts(4),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="cccccccc-0000-0000-0000-000000000003",
            cwd="/work/gone",
            classification="irrecoverable",
            classification_reason="missing_jsonl_on_disk",
            state_summary="gone",
            user_notes=None,
            last_scanned=_ts(3),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="dddddddd-0000-0000-0000-000000000004",
            cwd="/work/weird",
            classification="borderline",
            classification_reason="unknown_tail_kind",
            state_summary="weird tail",
            user_notes=None,
            last_scanned=_ts(2),
            first_seen=_ts(0),
        ),
        DbFixtureRow(
            uuid="eeeeeeee-0000-0000-0000-000000000005",
            cwd="/work/dangling",
            classification="borderline",
            classification_reason="no_liveness_dangling_tool_use",
            state_summary="dangling",
            user_notes=None,
            last_scanned=_ts(1),
            first_seen=_ts(0),
        ),
    ]


def test_render_lean_collapses_bulk_to_counts(tmp_path: Path) -> None:
    """Lean mode keeps actionable rows full and collapses bulk (concluded,
    irrecoverable, unrecognised endings) to a count summary — so the triage read
    answers "what crashed" without dumping the whole ledger."""
    db_path = make_db_with_sessions(tmp_path, _lean_fixture_sessions())
    lean, count = render.render(db_path, show_all=False)

    # Row count is unaffected by the view.
    assert count == 5

    # Bulk sections are NOT rendered as full sections in lean mode.
    assert "## Recently concluded" not in lean
    assert "## Irrecoverable" not in lean
    # Bulk rows' UUIDs are not rendered as entries.
    assert "bbbbbbbb" not in lean  # concluded
    assert "cccccccc" not in lean  # irrecoverable
    assert "dddddddd" not in lean  # unknown_tail_kind (unrecognised)

    # Actionable rows ARE rendered in lean mode.
    assert "## Probable system-crash victims" in lean
    assert "aaaaaaaa-0000-0000-0000-000000000001" in lean  # crash victim
    assert "eeeeeeee-0000-0000-0000-000000000005" in lean  # dangling signal

    # Collapsed summary present with per-category counts and total.
    assert "## Collapsed" in lean
    assert "- Recently concluded: 1" in lean
    assert "- Irrecoverable: 1" in lean
    assert "- Unrecognised endings: 1" in lean
    assert "- Total tracked sessions: 5" in lean


def test_render_show_all_is_the_full_roster(tmp_path: Path) -> None:
    """The default (show_all=True) renders every row in its section and adds no
    Collapsed summary — preserving all-means-all for ~/llm-resume.md."""
    db_path = make_db_with_sessions(tmp_path, _lean_fixture_sessions())
    full, count = render.render(db_path)  # default show_all=True

    assert count == 5
    assert "## Recently concluded" in full
    assert "## Irrecoverable" in full
    for short in ("aaaaaaaa", "bbbbbbbb", "cccccccc", "dddddddd", "eeeeeeee"):
        assert short in full
    assert "## Collapsed" not in full


def test_render_lean_empty_filesystem_has_no_collapsed_section(tmp_path: Path) -> None:
    """Lean mode on an empty DB collapses nothing, so no Collapsed summary appears
    — the lean view stays minimal."""
    db_path = make_db_with_sessions(tmp_path, [])
    lean, _ = render.render(db_path, show_all=False)
    assert "## Collapsed" not in lean
    # The actionable crash-victims header is still present (so "0 crashes" reads).
    assert "## Probable system-crash victims" in lean


def test_render_lean_still_shows_uncorrelated_markers(tmp_path: Path) -> None:
    """Lean mode collapses the session bulk but keeps uncorrelated markers FULL —
    crash evidence is never collapsed (Gap A), even alongside a Collapsed summary."""
    db_path = make_db_with_sessions(tmp_path, _lean_fixture_sessions())
    _insert_uncorrelated_marker(
        db_path,
        boot_id="85c5ebd8-12c1-4200-915a-d29845a0667e",
        pid=663495,
        cwd="/work/bjet",
        started=1_781_682_073,
        reason="dead_pid",
        last_scanned=1_781_900_000,
    )
    lean, _ = render.render(db_path, show_all=False)
    # The marker section renders in full despite lean mode.
    assert "## Uncorrelated crash markers" in lean
    assert "663495" in lean
    assert "/work/bjet" in lean
    # The session bulk is still collapsed.
    assert "## Collapsed" in lean
    assert "## Recently concluded" not in lean

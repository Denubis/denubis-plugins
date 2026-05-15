# denubis-crash-recovery Implementation Plan — Phase 2: JSONL tail parser and classification rule table

**Goal:** Pure-function classifier from JSONL tail state + liveness inputs to a `Classification` value with a citable reason.

**Architecture:** Two modules. `crash_recovery.jsonl` reads the last N lines of a session JSONL with a memory-bounded `deque(maxlen=N)` and produces a frozen `TailSummary`. `crash_recovery.classify` declares an immutable `RULES` tuple of frozen `Rule` rows with structured matchers; `classify(tail_summary, liveness_state, pid_alive)` walks the table and returns the first match. `CLASSIFIER_VERSION: int = 1` lives in `classify.py` and is written by Phase 4's scan onto every persisted row.

**Tech Stack:** Python 3.12+, `json` / `collections.deque` / `dataclasses` / `enum` (stdlib only), pytest.

**Scope:** Phase 2 of 8 from `docs/design-plans/2026-05-08-crash-recovery.md`.

**Codebase verified:** 2026-05-13 (Phase 2B investigator report — three real JSONLs sampled; top-level `type` discriminator, `message.stop_reason`, `message.content[].type`, `tool_use_id` matching confirmed; attachments interleave between tool_use and tool_result).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and tests:

### crash-recovery.AC3: Classification is deterministic
- **crash-recovery.AC3.1 Success:** Every row of the rule table classifies its fixture to the expected value (parametrised tests; one assertion per row)
- **crash-recovery.AC3.3 Success:** Each session row records a non-empty `classification_reason` string referencing the rule that matched
- **crash-recovery.AC3.4 Failure:** A JSONL with a malformed JSON line yields classification `borderline` with reason `malformed_tail`; the CLI does not crash
- **crash-recovery.AC3.5 Edge:** An empty JSONL (zero entries) yields `borderline` with reason `empty_file`

> AC3.2 (byte-identical scan+render markdown) is deferred to Phase 5 — that AC requires the render pipeline, not just the classifier.
> AC3.6 (re-classification of `classifier_version`-stale rows) is deferred to Phase 4 — that AC requires the scan walk over DB rows, not just the `CLASSIFIER_VERSION` constant.

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: `crash_recovery.jsonl` — TailSummary + parse_tail

**Verifies:** Indirectly AC3.4 and AC3.5 (failure-mode TailKinds); fully verified once Task 5's parametrised tests run.

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/jsonl.py`

**Implementation:**

The module exposes:

1. **`TailKind`** — enum of trailing-tail shapes, matching the design's hard-crash signatures plus the failure modes:

   - `CONCLUDED` — last assistant entry is `stop_reason == "end_turn"` with text-only content; no unmatched tool dispatches.
   - `TOOL_USE_NO_RESULT` — last assistant entry dispatched a `tool_use` (name ≠ `AskUserQuestion`, name ≠ `Task`), no matching `tool_result` follows.
   - `ASK_QUESTION_NO_REPLY` — last assistant entry dispatched `tool_use` with `name == "AskUserQuestion"`, no follow-up user entry with `toolUseResult.answers` populated.
   - `AGENT_DISPATCH_NO_RESULT` — last assistant entry dispatched `tool_use` with `name == "Task"`, no matching `tool_result` follows.
   - `EMPTY` — file exists but has zero JSON lines.
   - `MALFORMED_TAIL` — at least one line in the read window failed to parse as JSON.
   - `MISSING_FILE` — file path does not exist on disk.
   - `UNKNOWN` — file parsed cleanly but the tail does not match any other kind (e.g., trailing system/attachment-only entries; fallback for surprises).

2. **`TailSummary`** — frozen `@dataclass(frozen=True)`:

   ```python
   @dataclass(frozen=True)
   class TailSummary:
       kind: TailKind
       last_ts: int | None        # unix epoch (seconds) parsed from `timestamp`; None if unknown
       total_entries: int          # number of JSON-parseable lines observed in the read window
       state_summary: str          # one-line human-readable description for sessions.state_summary
   ```

3. **`parse_tail(path: Path, n: int = 20) -> TailSummary`** — read last `n` lines using `collections.deque(maxlen=n)`, JSON-parse each, then walk the parsed window from the end forwards to determine `TailKind`. Specifics:

   - If `path` does not exist: return `TailSummary(kind=MISSING_FILE, last_ts=None, total_entries=0, state_summary="jsonl missing on disk")`.
   - If file exists but is empty (zero lines or zero bytes): return `TailSummary(kind=EMPTY, ..., state_summary="empty jsonl")`.
   - Open the file with `path.open("r", encoding="utf-8")` and iterate via `tail = deque(f, maxlen=n)`.
   - Try to `json.loads()` each line in `tail`; any `json.JSONDecodeError` flips the kind to `MALFORMED_TAIL` (continue parsing the rest for state_summary, but the final classification is `MALFORMED_TAIL`).
   - Filter parsed entries: drop entries whose top-level `type` is `system`, `attachment`, `file-history-snapshot`, `last-prompt`, `ai-title`, or `permission-mode` — these are bookkeeping per Phase 2B investigation.
   - Walk the filtered window from the end:
     - Last entry is assistant with `message.stop_reason == "end_turn"` and all `message.content[]` items typed `text` → `CONCLUDED`.
     - Last assistant entry has a `tool_use` content item; check whether any later user entry (after this dispatch in the original window) carries a `tool_result` with matching `tool_use_id` OR a `toolUseResult.answers` (for AskUserQuestion). If not, classify by the tool name:
       - `name == "AskUserQuestion"` → `ASK_QUESTION_NO_REPLY`
       - `name == "Task"` → `AGENT_DISPATCH_NO_RESULT`
       - otherwise → `TOOL_USE_NO_RESULT`
     - Otherwise → `UNKNOWN`.
   - `last_ts` = unix epoch (int) parsed from the very last filtered entry's `timestamp` field via `datetime.fromisoformat(...).timestamp()` (treat trailing `Z` as UTC).
   - `state_summary` = a one-line string. Examples: `"concluded — end_turn at 2026-05-13T03:00:12Z"`, `"tool_use no result: Bash dispatched at 2026-05-13T03:00:12Z"`, `"malformed json at tail (entries -1)"`, `"empty jsonl"`. Keep under 120 characters.

**Critical implementation note:** the parser MUST scan forward through the read window to find matching `tool_use_id` results, NOT assume immediate adjacency. Attachments (hook outputs) interleave between dispatch and result.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery.jsonl import parse_tail, TailKind
import tempfile, json, pathlib
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / 'concluded.jsonl'
    p.write_text(json.dumps({
        'type': 'assistant',
        'timestamp': '2026-05-13T03:00:12.000Z',
        'message': {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': 'done'}]}
    }) + '\n')
    summary = parse_tail(p)
    assert summary.kind is TailKind.CONCLUDED, summary
    print('OK:', summary.state_summary)
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/jsonl.py
git commit -m "feat(crash-recovery): add jsonl module with TailSummary and parse_tail"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Tests for `parse_tail` — happy paths and failure modes

**Verifies:** AC3.4 (malformed_tail), AC3.5 (empty_file); also exercises every `TailKind` enumerated in Task 1.

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_jsonl_tail.py`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/__init__.py` (empty)
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py`

**Implementation:**

`fixtures/jsonl_builder.py` exposes helpers that write minimal JSONL files for each `TailKind`. One helper per kind:

- `make_concluded(path)` → writes an assistant entry with `stop_reason == "end_turn"` and a text content item.
- `make_tool_use_no_result(path, tool_name="Bash")` → writes an assistant entry dispatching `tool_name`, no follow-up user `tool_result`.
- `make_ask_question_no_reply(path)` → assistant entry with `tool_use.name == "AskUserQuestion"`, no `toolUseResult.answers`.
- `make_agent_dispatch_no_result(path)` → assistant entry with `tool_use.name == "Task"`, no follow-up result.
- `make_empty(path)` → creates an empty file.
- `make_malformed_tail(path)` → writes 3 valid entries followed by a line that is not valid JSON.
- `make_attachment_interleaved_then_concluded(path)` → assistant `tool_use`, then `attachment` (hook_success), then matching user `tool_result`, then assistant text end_turn. Used to assert the parser does NOT mis-classify interleaved attachments as crash signatures.

Each helper accepts the destination `Path` and returns nothing (writes JSONL to disk via `path.write_text(json.dumps(entry) + "\n" for entry in entries)`). Timestamps in fixtures use a fixed UTC string to keep `last_ts` deterministic.

**`test_jsonl_tail.py` tests (all unit; touch the filesystem via `tmp_path`):**

- `test_parse_tail_classifies_concluded` → call `make_concluded`, assert `parse_tail(...).kind is TailKind.CONCLUDED`, assert `state_summary` is non-empty.
- `test_parse_tail_classifies_tool_use_no_result` → `make_tool_use_no_result`, assert kind matches.
- `test_parse_tail_classifies_ask_question_no_reply` → assert kind matches.
- `test_parse_tail_classifies_agent_dispatch_no_result` → assert kind matches.
- `test_parse_tail_handles_attachment_interleave` → `make_attachment_interleaved_then_concluded`, assert kind is `CONCLUDED` (NOT `TOOL_USE_NO_RESULT`).
- `test_parse_tail_classifies_empty_file_as_empty` → `make_empty`, assert kind is `EMPTY`, state_summary mentions `empty` (AC3.5).
- `test_parse_tail_classifies_malformed_tail` → `make_malformed_tail`, assert kind is `MALFORMED_TAIL`, state_summary references the malformation (AC3.4).
- `test_parse_tail_handles_missing_file` → pass a path that does not exist, assert kind is `MISSING_FILE`; assert NO exception raised.
- `test_parse_tail_respects_n_window` → write 1000 entries (alternating user/assistant), `parse_tail(path, n=10)` should return a summary whose `total_entries` equals 10.
- `test_parse_tail_extracts_last_ts` → fixture with timestamp `2026-05-13T03:00:12.000Z`; assert `last_ts == int(datetime(2026,5,13,3,0,12, tzinfo=timezone.utc).timestamp())`.

**Step: Verify operationally**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_jsonl_tail.py -q
```

Expected: all tests pass.

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/tests/
git commit -m "test(crash-recovery): cover parse_tail for every TailKind including failure modes"
```
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

---

<!-- START_SUBCOMPONENT_B (tasks 3-5) -->

<!-- START_TASK_3 -->
### Task 3: `crash_recovery.classify` — types and constants

**Verifies:** none directly (foundation for Tasks 4 and 5).

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/classify.py`

**Implementation:**

```python
"""Deterministic classification of Claude Code sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

CLASSIFIER_VERSION: int = 1
"""Bump when RULES changes shape. Scan re-classifies any row whose stored
classifier_version is below this constant. See design plan DR9."""


class ClassificationValue(StrEnum):
    LIVE = "live"
    HARD_CRASH = "hard_crash"
    BORDERLINE = "borderline"
    CONCLUDED = "concluded"
    IRRECOVERABLE = "irrecoverable"


@dataclass(frozen=True)
class Classification:
    value: ClassificationValue
    reason: str
```

`StrEnum` gives us serialisable string values directly usable as SQLite `TEXT` column values (matches the design's `classification TEXT NOT NULL` column type) without manual conversion.

The `Rule` dataclass and `RULES` table land in Task 4 — kept separate so the test file (Task 5) can import `Classification`/`ClassificationValue` independently from `RULES`.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery.classify import Classification, ClassificationValue, CLASSIFIER_VERSION
c = Classification(value=ClassificationValue.LIVE, reason='live_pid_present_boot_current')
assert c.value == 'live'  # StrEnum serialises as string
assert CLASSIFIER_VERSION == 1
print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/classify.py
git commit -m "feat(crash-recovery): add classify module types and CLASSIFIER_VERSION=1"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Rule table and `classify()` function

**Verifies:** AC3.3 (every Classification carries a non-empty reason); fully verified by Task 5.

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/classify.py`

**Implementation:**

Add to `classify.py`:

1. **`LivenessState`** type — a small frozen dataclass exposing what the classifier needs to know about the liveness signal:

   ```python
   @dataclass(frozen=True)
   class LivenessState:
       present: bool          # is there a liveness file describing this session?
       boot_id_current: bool  # if present, does the recorded boot_id match the current boot?
   ```

   `pid_alive: bool | None` is passed as a separate argument to `classify()` (None when no liveness file exists, otherwise the result of `kill -0` from Phase 3).

2. **`Rule`** frozen dataclass with structured matchers — each field is `Optional`; `None` = wildcard:

   ```python
   from typing import Optional
   from crash_recovery.jsonl import TailKind

   @dataclass(frozen=True)
   class Rule:
       trailing_kind: Optional[TailKind]
       liveness_present: Optional[bool]
       pid_alive: Optional[bool]
       boot_id_current: Optional[bool]
       classification: ClassificationValue
       reason: str
   ```

3. **`RULES: tuple[Rule, ...]`** — declarative, most-specific first. The rows below cover the partition the design specifies; the implementation MUST keep them in this order so first-match semantics produce the right answer.

   The rule set (one row per design-named outcome). Each row's `reason` string is the slug the test parametrisation will assert against:

   - **irrecoverable_missing_jsonl** — `trailing_kind=MISSING_FILE` → `ClassificationValue.IRRECOVERABLE`, reason `"missing_jsonl_on_disk"`.
   - **borderline_malformed_tail** — `trailing_kind=MALFORMED_TAIL` → `ClassificationValue.BORDERLINE`, reason `"malformed_tail"` (AC3.4).
   - **borderline_empty_file** — `trailing_kind=EMPTY` → `ClassificationValue.BORDERLINE`, reason `"empty_file"` (AC3.5).
   - **hard_crash_boot_mismatch** — `liveness_present=True, boot_id_current=False` → `ClassificationValue.HARD_CRASH`, reason `"liveness_boot_id_mismatch"` (boot mismatch is sufficient evidence per design DR7).
   - **live_pid_present** — `liveness_present=True, pid_alive=True, boot_id_current=True` → `ClassificationValue.LIVE`, reason `"live_pid_present_boot_current"`.
   - **hard_crash_tool_use** — `liveness_present=True, pid_alive=False, boot_id_current=True, trailing_kind=TOOL_USE_NO_RESULT` → `ClassificationValue.HARD_CRASH`, reason `"liveness_dead_pid_tool_use_no_result"`.
   - **hard_crash_ask_question** — same as above but `trailing_kind=ASK_QUESTION_NO_REPLY` → reason `"liveness_dead_pid_ask_question_no_reply"`.
   - **hard_crash_agent_dispatch** — same as above but `trailing_kind=AGENT_DISPATCH_NO_RESULT` → reason `"liveness_dead_pid_agent_dispatch_no_result"`.
   - **hard_crash_dead_pid_unknown_tail** — `liveness_present=True, pid_alive=False, boot_id_current=True, trailing_kind=UNKNOWN` → reason `"liveness_dead_pid_unknown_tail"`.
   - **concluded_no_liveness_clean_tail** — `liveness_present=False, trailing_kind=CONCLUDED` → `ClassificationValue.CONCLUDED`, reason `"no_liveness_clean_end_turn"`.
   - **borderline_no_liveness_dangling** — `liveness_present=False, trailing_kind=TOOL_USE_NO_RESULT` → `ClassificationValue.BORDERLINE`, reason `"no_liveness_dangling_tool_use"`.
   - **borderline_no_liveness_dangling_ask** — same with `ASK_QUESTION_NO_REPLY` → reason `"no_liveness_dangling_ask_question"`.
   - **borderline_no_liveness_dangling_agent** — same with `AGENT_DISPATCH_NO_RESULT` → reason `"no_liveness_dangling_agent_dispatch"`.
   - **borderline_unknown_tail** — catch-all `trailing_kind=UNKNOWN` (any liveness state not already matched) → `ClassificationValue.BORDERLINE`, reason `"unknown_tail_kind"`.

   Add an explicit comment block above `RULES` documenting "first-match semantics; reorder with care; each row must be paired with a fixture in `tests/test_classify.py`."

4. **`classify(tail_summary, liveness_state, pid_alive) -> Classification`**:

   ```python
   def classify(
       tail_summary: "TailSummary",
       liveness_state: LivenessState,
       pid_alive: Optional[bool],
   ) -> Classification:
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
       # No rule matched: deliberate review-queue route. The rule table covers
       # common cases; `unmatched` is the explicit "go look at this manually"
       # signal for realistic combinations the rules don't speak to (e.g., a
       # concluded JSONL paired with a liveness file whose PID is dead but boot
       # is still current — possible during scan/kill race conditions).
       # AC3.3 (non-empty classification_reason) is preserved.
       return Classification(value=ClassificationValue.BORDERLINE, reason="unmatched")
   ```

   The `unmatched` route is a deliberate output of the rule table, not a programmer-error fallback. Phase 5's render surfaces it with a distinct "Something fucky — let's go look" message, and Phase 7's triage skill tags such entries for manual review. Task 5 includes a partition-documenting test that enumerates the realistic combinations expected to land here.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery.classify import classify, LivenessState, RULES, ClassificationValue
from crash_recovery.jsonl import TailSummary, TailKind
ts = TailSummary(kind=TailKind.CONCLUDED, last_ts=0, total_entries=1, state_summary='x')
ls = LivenessState(present=False, boot_id_current=False)
c = classify(ts, ls, pid_alive=None)
assert c.value == ClassificationValue.CONCLUDED, c
assert c.reason, c
print(f'OK: {c.value} ({c.reason}); {len(RULES)} rules in table')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/classify.py
git commit -m "feat(crash-recovery): add Rule table and classify() with first-match semantics"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Parametrised tests for the rule table

**Verifies:** crash-recovery.AC3.1 (every row matches its fixture), crash-recovery.AC3.3 (non-empty reason), crash-recovery.AC3.4 (malformed_tail), crash-recovery.AC3.5 (empty_file).

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_classify.py`

**Implementation:**

The tests use `pytest.mark.parametrize` over `RULES` directly. For each rule, the fixture is constructed by mirroring the rule's matcher fields into concrete inputs.

Required tests:

- **`test_every_rule_classifies_its_fixture`** — parametrise over `RULES`. For each `rule`:
  - Build a `TailSummary` whose `kind` matches `rule.trailing_kind` (or pick any kind if wildcard).
  - Build a `LivenessState` with `present=rule.liveness_present` (or default True if wildcard).
  - Pass `pid_alive=rule.pid_alive` (or `None` if wildcard).
  - Assert `classify(tail_summary, liveness_state, pid_alive).value == rule.classification`.
  - Assert `classify(...).reason == rule.reason`.

  Covers AC3.1 (one assertion per row) and AC3.3 (non-empty reason).

- **`test_classify_is_idempotent`** — call `classify(...)` twice with identical inputs; assert results are `==` (frozen dataclass equality). Implicit but worth pinning.

- **`test_malformed_tail_maps_to_borderline_malformed_tail`** — explicitly: TailSummary with `kind=MALFORMED_TAIL`, any liveness; assert `Classification(value=BORDERLINE, reason="malformed_tail")`. Covers AC3.4 in a stand-alone test (not just rolled into the parametrisation) so a future rule-table refactor that breaks AC3.4 fails loudly.

- **`test_empty_jsonl_maps_to_borderline_empty_file`** — same shape for `EMPTY`. Covers AC3.5.

- **`test_unmatched_route_returns_borderline_unmatched`** — synthesise a realistic input combination that no rule covers, e.g., `TailKind.CONCLUDED + LivenessState(present=True, boot_id_current=True) + pid_alive=False` (a concluded session whose liveness file still records a now-dead PID on a still-current boot — a scan/kill race). Assert the result is `Classification(value=BORDERLINE, reason="unmatched")` with non-empty reason (AC3.3 guard).

- **`test_rules_table_partition_documents_unmatched_cases`** — enumerate the input combinations expected to route to `unmatched`. For v0.1.0 the documented set is:
  - `TailKind.CONCLUDED + LivenessState(present=True, boot_id_current=True) + pid_alive=False` (scan/kill race on a concluded session).
  - `TailKind.UNKNOWN + LivenessState(present=True, boot_id_current=True) + pid_alive=False` is covered by `borderline_unknown_tail` — INCLUDED here only as a negative example to assert it does NOT land in `unmatched`.
  - Any other combinations encountered during integration testing are added to this list; the test is the documentation. For each entry, parametrise: assert `classify(...)` returns `Classification(value=BORDERLINE, reason="unmatched")` for the positive cases, and the rule-specified reason for the negative cases. When a new rule is added that covers a previously-unmatched combination, remove it from the positive set in the same commit.

- **`test_classify_returns_classification_value_strenum`** — assert `classify(...).value` is a member of `ClassificationValue` (a `StrEnum`) and serialises as the documented strings (`"live"`, `"hard_crash"`, etc.). Protects against silent enum renames.

- **`test_rules_have_unique_reasons`** — assert that within `RULES`, every `(classification, reason)` pair is unique. Catches copy-paste errors when extending the table.

**Step: Verify operationally**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_classify.py -q
```

Expected: all tests pass. The parametrised test should report one passing case per row in `RULES` (currently 14 rows by Task 4's enumeration).

**Step: Confirm Phase 2 done-when criteria**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/ -q
```

Expected: all Phase 1 + Phase 2 tests pass. Repo-root `uv run pytest -q` should also pass.

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_classify.py
git commit -m "test(crash-recovery): parametrise rule table; cover AC3.1, AC3.3, AC3.4, AC3.5"
```
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_B -->

---

## Phase 2 Done When

- `crash_recovery.jsonl` exposes `parse_tail()` returning a `TailSummary` whose `kind` is one of the documented `TailKind` values for each fixture.
- `crash_recovery.classify` exposes `classify()` plus `CLASSIFIER_VERSION = 1`; every rule in `RULES` matches its synthetic fixture.
- Parametrised tests pass with one assertion per row of `RULES`; failure-mode tests pass for `MALFORMED_TAIL` and `EMPTY`.
- `classify()` returns identical `Classification` objects on identical inputs (idempotency).
- Repo-root `uv run pytest -q` passes (Phase 1 + Phase 2 tests).

## Outstanding for later phases

- AC3.2 (byte-identical scan+render markdown) → Phase 5.
- AC3.6 (re-classify stale `classifier_version` rows in DB) → Phase 4.
- Boot-aware liveness wiring (`LivenessState.boot_id_current`) — Phase 2 accepts it as input; Phase 3 produces it; Phase 4 wires the two together.
- PID-alive check (`pid_alive` argument) — Phase 2 accepts it; Phase 3 implements `pid_alive()`; Phase 4 wires.

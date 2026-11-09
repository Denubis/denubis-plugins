"""Continuation decisions independent of Codex transport and model I/O."""

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class Snapshot:
    thread_id: str
    cwd: str
    status: str
    history: list[dict[str, Any]]
    workers: dict[str, str] = field(default_factory=dict)
    complete: bool = True
    latest_turn_id: str = ""
    history_key: str = ""
    worker_evidence: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


@dataclass(frozen=True)
class Review:
    decision: str
    reason: str
    evidence: list[str]
    next_action: str


@dataclass
class ThreadState:
    thread_id: str
    cwd: str
    signal: str = "idle"
    paused: bool = False
    ended: bool = False
    generation: int = 0
    reviewed: str = ""
    users: str = ""
    progress: str = ""
    stalls: int = 0
    failures: int = 0
    retry_at: float = 0
    active_workers: bool = False
    failure_snapshot: str = ""
    last_error: str = ""
    last_outcome: str = ""
    pending_wake: str = ""
    last_decision: str = ""
    last_reason: str = ""
    last_evidence: list[str] = field(default_factory=list)
    last_action: str = ""


class ReviewError(RuntimeError):
    """The independent reviewer failed or returned an unusable decision."""


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def fingerprint(view: Snapshot) -> str:
    return digest(
        [
            view.thread_id,
            view.cwd,
            view.status,
            view.history_key or digest(view.history),
            view.workers,
            view.worker_evidence,
            view.complete,
            view.latest_turn_id,
        ]
    )


def user_messages(view: Snapshot) -> list[dict[str, Any]]:
    return [item for item in view.history if item.get("type") == "userMessage"]


def _semantic_evidence(items: list[dict[str, Any]]) -> list[str]:
    """Count new action/result evidence without counting transport event churn."""
    metadata = {
        "id",
        "durationMs",
        "processId",
        "startedAtMs",
        "completedAtMs",
        "turnId",
    }
    return sorted(
        {
            digest({key: value for key, value in item.items() if key not in metadata})
            for item in items
        }
    )


def progress_key(view: Snapshot) -> str:
    actions = [
        item
        for item in view.history
        if item.get("type") not in {"agentMessage", "reasoning", "userMessage"}
        and not (
            item.get("type") == "functionCallOutput"
            and item.get("namespace") == "carry_on"
            and item.get("name") == "continuation_review"
        )
    ]
    workers = {
        key: _semantic_evidence(items) for key, items in view.worker_evidence.items()
    }
    return digest(
        [user_messages(view), _semantic_evidence(actions), view.workers, workers]
    )


def _eligible(state: ThreadState, view: Snapshot) -> str | None:
    messages = user_messages(view)
    if messages:
        users = digest(messages)
        if state.users and state.users != users:
            state.paused = False
            state.stalls = 0
        state.users = users
    if state.ended or state.paused or view.status != "idle":
        return "inactive"
    if not view.complete or not user_messages(view):
        return "insufficient_context"
    active = any(status in {"active", "unknown"} for status in view.workers.values())
    if state.active_workers and not active:
        state.signal = "workers_done"
    state.active_workers = active
    if active and state.signal == "idle":
        return "workers_running"
    return None


def _review_failure(state: ThreadState, key: str, now: float, error: str) -> str:
    state.failure_snapshot = key
    state.failures += 1
    state.retry_at = now + 10 * (2 ** (state.failures - 1))
    state.last_error = error
    return "review_failed"


def _skip_review(state: ThreadState, view: Snapshot, now: float) -> str | None:
    reason = _eligible(state, view)
    if reason:
        return reason
    key = fingerprint(view)
    if state.pending_wake == key:
        return "delivery_uncertain"
    state.pending_wake = ""
    if key == state.reviewed:
        return "unchanged"
    if key != state.failure_snapshot:
        state.failures = 0
        state.retry_at = 0
    if state.failures >= 3 or now < state.retry_at:
        return "retry_limited"
    if progress_key(view) != state.progress:
        state.stalls = 0
    return "no_progress" if state.stalls >= 2 else None


class Backend(Protocol):
    def snapshot(self, thread_id: str) -> Snapshot: ...

    def wake(self, thread_id: str, message: str) -> None: ...


def check_thread(
    state: ThreadState,
    backend: Backend,
    reviewer: Callable[[Snapshot, str], Review],
    *,
    now: float,
    still_current: Callable[[ThreadState], bool] | None = None,
    reserve: Callable[[ThreadState], bool] | None = None,
) -> str:
    """Review an enrolled idle thread, recheck it, then continue authorized work."""
    view = backend.snapshot(state.thread_id)
    reason = _skip_review(state, view, now)
    if reason:
        return reason
    key = fingerprint(view)
    progress = progress_key(view)
    generation = state.generation
    try:
        review = reviewer(view, state.signal)
    except ReviewError as error:
        return _review_failure(state, key, now, str(error))
    current = backend.snapshot(state.thread_id)
    if (
        fingerprint(current) != key
        or state.generation != generation
        or state.paused
        or state.ended
        or (still_current is not None and not still_current(state))
    ):
        return "stale"
    state.failures = 0
    state.last_error = ""
    state.signal = "idle"
    state.last_decision = review.decision
    state.last_reason = review.reason
    state.last_evidence = review.evidence
    state.last_action = review.next_action
    if review.decision != "continue":
        state.reviewed = key
        return review.decision
    return _wake(state, backend, review, key, progress, reserve=reserve)


def _wake(
    state: ThreadState,
    backend: Backend,
    review: Review,
    key: str,
    progress: str,
    *,
    reserve: Callable[[ThreadState], bool] | None,
) -> str:
    message = (
        "[carry-on] An independent completion check found authorized work remaining. "
        "Continue within the user's existing instructions; respect interruptions, "
        "approval requirements, and unanswered human decisions.\n"
        f"Evidence: {'; '.join(review.evidence)}\n"
        f"Next action: {review.next_action}"
    )
    state.pending_wake = key
    state.progress = progress
    state.stalls += 1
    state.last_error = "Wake delivery is uncertain until the daemon confirms it"
    if reserve is not None and not reserve(state):
        return "stale"
    try:
        backend.wake(state.thread_id, message)
    except RuntimeError as error:
        state.last_error = f"Wake delivery uncertain: {error}"
        return "delivery_uncertain"
    state.pending_wake = ""
    state.last_error = ""
    state.reviewed = key
    return "continued"

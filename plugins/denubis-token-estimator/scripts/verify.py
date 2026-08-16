#!/usr/bin/env python3
"""Reproducible audit harness for the token/word estimator methodology.

Every headline number in DESIGN.md is re-derived here directly from the live logs,
printed as COMPUTED vs ASSERTED with a PASS/FAIL. This exists because node 2 was
wrong for weeks: its prose said one thing, its number came from a different (broken)
computation, and nothing caught the gap. A claim that isn't a runnable probe is a
claim no one has checked.

This harness encodes OUR assumptions. An auditor must not trust it — re-running it
just reproduces our possibly-wrong reasoning (that is exactly how node 2 survived).
Use it as the starting point, then write INDEPENDENT probes to falsify the assumptions
called out in docs/AUDIT-BRIEF.md.

Usage:
  python3 verify.py            # human report
  python3 verify.py --json     # machine-readable results for an external auditor

Read-only. Stdlib only. Reads ~/.claude/projects and ~/.codex/sessions.
"""

from __future__ import annotations

import collections
import json
import re
import sys
import tomllib
from datetime import datetime
from itertools import pairwise
from pathlib import Path

CLAUDE_ROOT = Path.home() / ".claude" / "projects"
CODEX_ROOT = Path.home() / ".codex" / "sessions"


# People-roots are NOT hardcoded. They come from ~/.token-estimator (TOML) as a
# top-level `roots = [...]` array of absolute people-dir paths. Absent that file,
# the tool scopes to one local directory (target_dir or cwd) — so it works out of
# the box on "the project I'm in" without any global config.
def load_roots(target_dir=None):
    cfg = Path.home() / ".token-estimator"
    if cfg.exists():
        try:
            roots = (tomllib.loads(cfg.read_text(encoding="utf-8")) or {}).get("roots")
            if roots:
                return [str(Path(r).expanduser().resolve()) for r in roots]
        except OSError, tomllib.TOMLDecodeError:
            pass
    return [str(Path(target_dir).resolve() if target_dir else Path.cwd())]


ROOTS = load_roots()

# Machine-emitted wrapper tags (node 3). Exclusion is an ALLOW-LIST of machine tags,
# NOT "text starts with '<'": humans paste <p>/<div>/<style> as genuine content.
MACHINE_TAGS = {
    "system-reminder",
    "command-name",
    "command-message",
    "command-args",
    "command-stdout",
    "command-stderr",
    "local-command-stdout",
    "local-command-stderr",
    "local-command-caveat",
    "task-notification",
    "teammate-message",
    "bash-input",
    "bash-stdout",
    "bash-stderr",
    "user-prompt-submit-hook",
}
_LEAD_TAG = re.compile(r"^\s*<([a-zA-Z][\w-]*)")

# Codex root-thread user-input machine markers (node 4), derived by signature-inspecting
# the live stream. Same allow-list discipline as node 3: machine is a NAMED set, not
# "starts with <" or "starts with #" — human prompts use markdown headings
# such as "# Claude ...", and pasted markup — both are kept.
CODEX_MACHINE_TAGS = {
    "turn_aborted",  # "<turn_aborted> The user interrupted ..." boilerplate
    "skill",  # injected SKILL.md contents
    "subagent_notification",  # subagent JSON status payloads
    "environment_context",  # injected cwd/shell/env block
    "user_instructions",  # injected instruction wrapper (defensive)
}


def codex_machine_marker(tx):
    s = tx.lstrip()
    if s.startswith("# AGENTS.md"):
        return "#AGENTS.md"  # session-opener, not the human's
    m = _LEAD_TAG.match(s)
    if m and m.group(1).lower() in CODEX_MACHINE_TAGS:
        return m.group(1).lower()
    return None


# ---- what we assert, split by stability ------------------------------------
# INVARIANTS must hold no matter how the corpus grows. A FAIL here is a real defect.
INVARIANT = {
    "node2_no_resumes": True,  # distinct codex ids == file count
    "node5_cross_person": 0,  # no message.id spans >1 person
    "node5_cross_person_project_max": 2,  # <=2 ids span >1 (person,project)
    "node2_counter_boundaries": True,
}
# BASELINES are point-in-time snapshots; absolute counts drift UP as logs accrue.
# Only the ratios (share %) should stay roughly constant. Recorded for reference.
BASELINE = {
    # 2026-06-18 snapshot; method, not the absolute, is audited
    "node1_share_pct": 20.2,
    "node2_main_tok": 6_284_838,
    "node2_sub_tok": 1_641_596,
    "node2_share_pct": 20.7,
    "node3_human_blocks": 22_049,
    "node4_turns": 1_351,
    "node4_words": 108_027,  # pinned 2026-06-18; no dedup (see node 4)
}
# Node 4 was unpinned; now re-derived from the live stream by signature inspection.
# The prior session's number is kept only as a historical contrast.
PRIOR_NODE4_UNRECONCILED = {
    "turns": 1_294,
    "words": 103_413,
}  # last session, superseded


def pct(a, b):
    return (a / b * 100.0) if b else 0.0


def claude_files():
    return list(CLAUDE_ROOT.rglob("*.jsonl"))


def codex_files():
    return list(CODEX_ROOT.rglob("rollout-*.jsonl")) if CODEX_ROOT.exists() else []


def attribute(cwd, roots=None):
    """Default derivation (no mapper). Returns (person, project, subdir)."""
    if not cwd:
        return ("(no-cwd)", "(no-cwd)", "")
    best = None
    for r in roots if roots is not None else ROOTS:
        if (cwd == r or cwd.startswith(r + "/")) and (
            best is None or len(r) > len(best)
        ):
            best = r
    if best is None:
        return ("(unrooted)", cwd, "")
    rem = cwd[len(best) :].lstrip("/")
    if rem == "":
        return ("(unrooted)", cwd, "")
    segs = rem.split("/")
    if len(segs) == 1:
        return (segs[0], "(person-root)", "")
    return (segs[0], segs[1], "/".join(segs[2:]))


def lead_tag(text):
    m = _LEAD_TAG.match(text)
    return m.group(1).lower() if m else None


# ---------------------------------------------------------------- Claude pass
def claude_pass():
    """One pass: node 1 (tokens/origin), node 5 (cwd/id), node 3 (human words)."""
    # node1/5: per message.id -> max out, occurrences (main/sub), cwd@max-out line
    out_max = collections.defaultdict(int)
    in_main = collections.defaultdict(bool)
    in_sub = collections.defaultdict(bool)
    cwd_atmax = {}  # id -> cwd of the line that set the running max
    cwds_all = collections.defaultdict(set)
    # node3
    blocks = 0
    words = 0
    seen_uuid = set()
    wrap_hist = collections.Counter()

    for fp in claude_files():
        is_subfile = "/subagents/" in str(fp)
        try:
            with fp.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"assistant"' not in line and '"user"' not in line:
                        continue
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    t = r.get("type")
                    if t == "assistant":
                        m = r.get("message") or {}
                        mid, model = m.get("id"), m.get("model")
                        if not mid or not model or "synthetic" in model:
                            continue
                        cwd = r.get("cwd")
                        is_main = not (is_subfile or r.get("isSidechain") is True)
                        if is_main:
                            in_main[mid] = True
                        else:
                            in_sub[mid] = True
                        cwds_all[mid].add(cwd)
                        out = (m.get("usage") or {}).get("output_tokens") or 0
                        # bind cwd to the MAX-token occurrence (node 5 rule)
                        if (
                            out > out_max[mid]
                            or (
                                out == out_max[mid]
                                and cwd_atmax.get(mid)
                                and str(cwd) < str(cwd_atmax[mid])
                            )
                        ) and out >= out_max[mid]:
                            cwd_atmax[mid] = cwd
                        out_max[mid] = max(out_max[mid], out)
                    elif t == "user" and not is_subfile:
                        if r.get("isSidechain") is True:
                            continue
                        if "toolUseResult" in r:
                            continue
                        if r.get("isMeta") is True:
                            continue
                        uid = r.get("uuid")
                        if uid in seen_uuid:
                            continue
                        seen_uuid.add(uid)
                        msg = r.get("message") or {}
                        content = msg.get("content")
                        texts = []
                        if isinstance(content, str):
                            texts = [content]
                        elif isinstance(content, list):
                            texts = [
                                b.get("text", "")
                                for b in content
                                if isinstance(b, dict) and b.get("type") == "text"
                            ]
                        for tx in texts:
                            if not tx or not tx.strip():
                                continue
                            tag = lead_tag(tx)
                            if tag in MACHINE_TAGS:
                                wrap_hist[tag] += 1
                                continue
                            blocks += 1
                            words += len(tx.split())
        except OSError:
            continue

    ids = set(out_max)
    main_tok = sum(out_max[i] for i in ids if in_main[i])
    sub_tok = sum(out_max[i] for i in ids if in_main[i] is False and in_sub[i])
    cross_part = sum(1 for i in ids if in_main[i] and in_sub[i])
    # node 5 reconciliation: distinct (person,project)/person per id over ALL its cwds
    cross_person = cross_pp = 0
    for i in ids:
        pps = {attribute(c)[:2] for c in cwds_all[i]}
        if len({p for p, _ in pps}) > 1:
            cross_person += 1
        if len(pps) > 1:
            cross_pp += 1
    return {
        "distinct_ids": len(ids),
        "main_tok": main_tok,
        "sub_tok": sub_tok,
        "share": pct(sub_tok, main_tok + sub_tok),
        "cross_partition": cross_part,
        "node3_blocks": blocks,
        "node3_words": words,
        "wrap_hist": dict(wrap_hist),
        "cross_person": cross_person,
        "cross_person_project": cross_pp,
    }


# ----------------------------------------------------------------- Codex pass
def parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_new_task(payload):
    return payload.get("type") == "agent_message" and any(
        isinstance(item, dict)
        and item.get("type") == "input_text"
        and "Message Type: NEW_TASK" in item.get("text", "")
        for item in payload.get("content") or []
    )


def codex_threads():
    """Return one child-owned output counter per Codex rollout thread.

    Newer subagent files replay the parent's cumulative token events before the
    first NEW_TASK message. After that boundary the child either continues the
    replay baseline or starts a fresh counter. Older files contain no replay
    boundary and retain the original per-file MAX rule.
    """
    raw_threads = []
    for fp in codex_files():
        thread = {
            "id": None,
            "parent": None,
            "kind": "main",
            "cwd": None,
            "start": None,
            "task_seq": None,
            "events": [],
            "user_texts": [],
            "file": str(fp),
        }
        try:
            fh = fp.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for seq, line in enumerate(fh):
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                record_type = record.get("type")
                payload = record.get("payload") or {}
                when = parse_timestamp(record.get("timestamp"))
                if record_type == "session_meta" and thread["id"] is None:
                    thread["id"] = payload.get("id")
                    thread["parent"] = payload.get("parent_thread_id") or payload.get(
                        "forked_from_id"
                    )
                    thread["kind"] = (
                        "sub" if isinstance(payload.get("source"), dict) else "main"
                    )
                    thread["cwd"] = payload.get("cwd")
                    thread["start"] = when
                elif (
                    record_type == "response_item"
                    and thread["task_seq"] is None
                    and _is_new_task(payload)
                ):
                    thread["task_seq"] = seq
                elif (
                    record_type == "event_msg" and payload.get("type") == "token_count"
                ):
                    output = (
                        (payload.get("info") or {}).get("total_token_usage") or {}
                    ).get("output_tokens")
                    if isinstance(output, (int, float)):
                        thread["events"].append((seq, when, int(output)))
                elif (
                    record_type == "response_item"
                    and payload.get("type") == "message"
                    and payload.get("role") == "user"
                ):
                    parts = [
                        item.get("text", "")
                        for item in payload.get("content") or []
                        if isinstance(item, dict) and item.get("text")
                    ]
                    if parts:
                        thread["user_texts"].append((when, "\n".join(parts)))
        if thread["id"]:
            raw_threads.append(thread)

    by_id = {thread["id"]: thread for thread in raw_threads}
    for thread in raw_threads:
        values = [value for _seq, _when, value in thread["events"]]
        raw_max = max(values, default=0)
        parent = by_id.get(thread["parent"])
        parent_max = (
            max((value for _seq, _when, value in parent["events"]), default=0)
            if parent
            else None
        )
        parent_at_fork = None
        if parent and thread["start"] is not None:
            parent_at_fork = max(
                (
                    value
                    for _seq, when, value in parent["events"]
                    if when is not None and when <= thread["start"]
                ),
                default=0,
            )

        task_seq = thread["task_seq"]
        replay_values = []
        own_values = values
        mode = "root"
        if thread["kind"] == "sub" and task_seq is None:
            mode = "legacy-independent"
        elif thread["kind"] == "sub":
            replay_values = [
                value for seq, _when, value in thread["events"] if seq < task_seq
            ]
            own_values = [
                value for seq, _when, value in thread["events"] if seq > task_seq
            ]
            mode = "fresh-counter"

        replay_baseline = max(replay_values, default=0)
        first_output = own_values[0] if own_values else None
        own_max = max(own_values, default=0)
        if thread["kind"] == "sub" and task_seq is not None and replay_baseline:
            if first_output is not None and first_output >= replay_baseline:
                mode = "continued-parent-counter"
            else:
                mode = "fresh-after-replay"
        output_tokens = (
            max(0, own_max - replay_baseline)
            if mode == "continued-parent-counter"
            else own_max
        )
        owned_events = [
            (
                when,
                max(0, value - replay_baseline)
                if mode == "continued-parent-counter"
                else value,
            )
            for seq, when, value in thread["events"]
            if task_seq is None or seq > task_seq
        ]
        thread.update(
            {
                "raw_max": raw_max,
                "parent_max": parent_max,
                "parent_at_fork": parent_at_fork,
                "replay_baseline": replay_baseline,
                "first_output": first_output,
                "counter_mode": mode,
                "output_tokens": output_tokens,
                "owned_events": owned_events,
                "own_counter_monotonic": all(
                    previous <= current for previous, current in pairwise(own_values)
                ),
            }
        )
    return raw_threads


def windowed_output(thread, start, end):
    """Return a cumulative counter's output produced in ``[start, end)``."""

    before_start = max(
        (
            value
            for when, value in thread["owned_events"]
            if when is not None and when < start
        ),
        default=0,
    )
    before_end = max(
        (
            value
            for when, value in thread["owned_events"]
            if when is not None and when < end
        ),
        default=0,
    )
    return max(0, before_end - before_start)


def codex_pass():
    """node 2 (tokens) + node 4 (human words), per rollout thread."""
    threads = codex_threads()
    main_tok = sum(
        thread["output_tokens"] for thread in threads if thread["kind"] == "main"
    )
    sub_tok = sum(
        thread["output_tokens"] for thread in threads if thread["kind"] == "sub"
    )
    n_main = sum(thread["kind"] == "main" for thread in threads)
    n_sub = sum(thread["kind"] == "sub" for thread in threads)
    n_turns = 0
    n_words = 0
    excl_hist = collections.Counter()
    for thread in threads:
        if thread["kind"] != "main":
            continue
        for _when, text in thread["user_texts"]:
            marker = codex_machine_marker(text)
            if marker:
                excl_hist[marker] += 1
                continue
            n_turns += 1
            n_words += len(text.split())

    subs = [thread for thread in threads if thread["kind"] == "sub"]
    replay_parent_mismatches = [
        thread["id"]
        for thread in subs
        if thread["replay_baseline"]
        and thread["parent_at_fork"] is not None
        and thread["replay_baseline"] != thread["parent_at_fork"]
    ]
    unresolved_replay_parents = [
        thread["id"]
        for thread in subs
        if thread["replay_baseline"] and thread["parent_at_fork"] is None
    ]
    post_task_nonmonotonic = [
        thread["id"]
        for thread in subs
        if thread["task_seq"] is not None and not thread["own_counter_monotonic"]
    ]
    # Old files have no NEW_TASK boundary. A large first value would mean the old
    # independent-counter assumption can no longer distinguish replay safely.
    legacy_large_starts = [
        thread["id"]
        for thread in subs
        if thread["counter_mode"] == "legacy-independent"
        and thread["first_output"] is not None
        and thread["first_output"] >= 2_000
    ]

    return {
        "files": len(threads),
        "n_main": n_main,
        "n_sub": n_sub,
        "main_tok": main_tok,
        "sub_tok": sub_tok,
        "share": pct(sub_tok, main_tok + sub_tok),
        "distinct_ids": len({thread["id"] for thread in threads}),
        "sub_all": [
            (thread["first_output"], thread["raw_max"], thread["parent_max"])
            for thread in subs
        ],
        "counter_modes": dict(
            collections.Counter(thread["counter_mode"] for thread in subs)
        ),
        "replay_parent_mismatches": replay_parent_mismatches,
        "unresolved_replay_parents": unresolved_replay_parents,
        "post_task_nonmonotonic": post_task_nonmonotonic,
        "legacy_large_starts": legacy_large_starts,
        "node4_turns": n_turns,
        "node4_words": n_words,
        "node4_excl": dict(excl_hist),
    }


# --------------------------------------------------------------------- report
def inv(name, ok, detail=""):
    return f"  [{'PASS' if ok else '**FAIL**'}] {name:<34} {detail}"


def base(name, computed, prior):
    delta = ""
    if isinstance(prior, (int, float)) and isinstance(computed, (int, float)):
        d = computed - prior
        delta = f"  (snapshot {prior}, Δ{'+' if d >= 0 else ''}{round(d, 2)})"
    return f"  [base] {name:<34} {computed}{delta}"


def main():
    want_json = "--json" in sys.argv
    sys.stderr.write("scanning Claude logs (one pass)...\n")
    c = claude_pass()
    sys.stderr.write("scanning Codex logs (one pass)...\n")
    x = codex_pass()

    if want_json:
        print(
            json.dumps(
                {
                    "claude": c,
                    "codex": x,
                    "invariant": INVARIANT,
                    "baseline": BASELINE,
                    "prior_node4_unreconciled": PRIOR_NODE4_UNRECONCILED,
                },
                indent=2,
            )
        )
        return

    boundary_ok = not (
        x["replay_parent_mismatches"]
        or x["unresolved_replay_parents"]
        or x["post_task_nonmonotonic"]
        or x["legacy_large_starts"]
    )
    print("=" * 78)
    print("AUDIT VERIFY — headline numbers re-derived from the live logs")
    print(
        "[PASS/FAIL] = structural invariant (must hold).  "
        "[base] = point-in-time (drifts up)."
    )
    print("=" * 78)

    print("\nNODE 1 — Claude output tokens (origin-based dedup)")
    print(base("subagent share %", round(c["share"], 1), BASELINE["node1_share_pct"]))
    print(
        f"        main={c['main_tok']:,}  sub={c['sub_tok']:,}  "
        f"ids={c['distinct_ids']:,}  cross-partition={c['cross_partition']}"
    )

    print("\nNODE 2 — Codex output tokens (per-thread, replay-aware)")
    print(
        inv(
            "node2 no resumes (ids==files)",
            x["distinct_ids"] == x["files"],
            f"ids={x['distinct_ids']} files={x['files']}",
        )
    )
    print(
        inv(
            "node2 counter boundaries",
            boundary_ok,
            f"modes={x['counter_modes']}; "
            f"unresolved replay parents={len(x['unresolved_replay_parents'])}; "
            f"replay/parent mismatches={len(x['replay_parent_mismatches'])}; "
            f"post-task nonmonotonic={len(x['post_task_nonmonotonic'])}; "
            f"ambiguous legacy starts={len(x['legacy_large_starts'])}",
        )
    )
    print(base("subagent share %", round(x["share"], 1), BASELINE["node2_share_pct"]))
    print(base("main_tok", x["main_tok"], BASELINE["node2_main_tok"]))
    print(base("sub_tok", x["sub_tok"], BASELINE["node2_sub_tok"]))
    print(f"        threads {x['n_main']} root / {x['n_sub']} sub")

    print("\nNODE 3 — Claude human words")
    print(base("human blocks", c["node3_blocks"], BASELINE["node3_human_blocks"]))
    print(
        f"        human words={c['node3_words']:,}   wrappers dropped: {c['wrap_hist']}"
    )

    print(
        "\nNODE 4 — Codex human words "
        "(re-derived; exclusion set from signature inspection)"
    )
    print(base("human turns", x["node4_turns"], BASELINE["node4_turns"]))
    print(base("human words", x["node4_words"], BASELINE["node4_words"]))
    print(f"        machine excluded: {x['node4_excl']}")
    print(
        "        KEPT as human (audit these): markdown-heading prompts (# Claude ...),"
    )
    print(
        "        pasted agent output (●…) and terminal pastes "
        "— owner's explicit choice."
    )
    print("        (prior session's unreproduced 1,294/103,413 now superseded.)")

    print("\nNODE 5 — attribution reconciliation")
    print(
        inv(
            "ids crossing >1 person == 0",
            c["cross_person"] == INVARIANT["node5_cross_person"],
            f"computed={c['cross_person']}",
        )
    )
    print(
        inv(
            "ids crossing >1 (person,project) <= 2",
            c["cross_person_project"] <= INVARIANT["node5_cross_person_project_max"],
            f"computed={c['cross_person_project']}",
        )
    )
    print(
        f"        => person rollups reconcile exactly; project to within "
        f"{c['cross_person_project']} ids of {c['distinct_ids']:,}"
    )

    print("\n" + "=" * 78)
    print("Re-running this only re-checks OUR arithmetic and encodes OUR assumptions.")
    print(
        "To audit the METHOD, attack the assumptions in docs/AUDIT-BRIEF.md with your"
    )
    print("own probes — that is how node 2 (and now node 4) were caught.")


if __name__ == "__main__":
    main()

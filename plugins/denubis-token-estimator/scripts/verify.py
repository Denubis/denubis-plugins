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
    "node2_subagent_additive": True,  # every sampled sub first_out << parent_max
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
def codex_pass():
    """node 2 (tokens) + node 4 (human words), per rollout file."""
    files = codex_files()
    main_tok = sub_tok = 0
    n_main = n_sub = 0
    sub_independence = []  # (first_out, max_out, parent_max) sample
    by_id = {}
    recs = []
    # node 4
    n_turns = 0
    n_words = 0
    excl_hist = collections.Counter()

    for fp in files:
        own_id = ff = None
        seen_meta = False
        mx = 0
        first_out = None
        kind = "main"
        user_texts = []
        with fp.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                t = r.get("type")
                p = r.get("payload") or {}
                if t == "session_meta" and not seen_meta:
                    own_id = p.get("id")
                    ff = p.get("forked_from_id")
                    s = p.get("source")
                    kind = "sub" if isinstance(s, dict) else "main"
                    seen_meta = True
                elif t == "event_msg" and p.get("type") == "token_count":
                    o = ((p.get("info") or {}).get("total_token_usage") or {}).get(
                        "output_tokens"
                    )
                    if isinstance(o, (int, float)):
                        o = int(o)
                        if first_out is None:
                            first_out = o
                        mx = max(mx, o)
                elif (
                    t == "response_item"
                    and p.get("type") == "message"
                    and p.get("role") == "user"
                ):
                    parts = [
                        c.get("text", "")
                        for c in (p.get("content") or [])
                        if isinstance(c, dict) and c.get("text")
                    ]
                    if parts:
                        user_texts.append("\n".join(parts))
        if not own_id:
            continue
        recs.append(
            {"id": own_id, "ff": ff, "kind": kind, "mx": mx, "first": first_out}
        )
        by_id[own_id] = recs[-1]
        if kind == "sub":
            sub_tok += mx
            n_sub += 1
        else:
            main_tok += mx
            n_main += 1
        # node 4: human words from ROOT threads only, per-thread text-set dedup
        if kind == "main":
            # No dedup: zero resumes in the corpus and response_item carries no
            # id, so each kept user message is a distinct human send. Repeated
            # "yes"/"continue"/"ok" are real human turns — text-set dedup would
            # silently delete them.
            for tx in user_texts:
                mk = codex_machine_marker(tx)
                if mk:
                    excl_hist[mk] += 1
                    continue
                n_turns += 1
                n_words += len(tx.split())

    # subagent independence — checked for ALL subagents, not a sample.
    # parented sub: first_out must be << parent total. parentless sub (ff absent):
    # first_out must be a fresh small start (the invariant is "counter does not
    # begin at a parent total").
    sub_all = []  # (first_out, own_max, parent_max_or_None)
    for rec in recs:
        if rec["kind"] == "sub":
            pm = by_id[rec["ff"]]["mx"] if rec["ff"] in by_id else None
            sub_all.append((rec["first"], rec["mx"], pm))
            if pm is not None:
                sub_independence.append((rec["first"], rec["mx"], pm))

    return {
        "files": len(files),
        "n_main": n_main,
        "n_sub": n_sub,
        "main_tok": main_tok,
        "sub_tok": sub_tok,
        "share": pct(sub_tok, main_tok + sub_tok),
        "distinct_ids": len({r["id"] for r in recs}),
        "sub_independence": sub_independence[:15],
        "sub_all": sub_all,
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

    # additive check over ALL subagents (not a sample): parented -> first << parent
    # total; parentless -> fresh small start. A "large start" means the counter may
    # continue a parent total (replay) -> additive model would over-count.
    FRESH = 2000

    def is_fresh(fo, _own, pm):
        if fo is None:
            return True  # no output events
        if pm is not None:
            return fo < 0.5 * pm
        return fo < FRESH  # parentless: must start fresh

    n_sub_checked = len(x["sub_all"])
    bad = [(fo, own, pm) for (fo, own, pm) in x["sub_all"] if not is_fresh(fo, own, pm)]
    add_ok = (n_sub_checked == x["n_sub"]) and (len(bad) == 0)
    max_first = max((fo for fo, _, _ in x["sub_all"] if fo is not None), default=0)
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

    print("\nNODE 2 — Codex output tokens (per-file, subagents additive)")
    print(
        inv(
            "node2 no resumes (ids==files)",
            x["distinct_ids"] == x["files"],
            f"ids={x['distinct_ids']} files={x['files']}",
        )
    )
    print(
        inv(
            "node2 subagents additive",
            add_ok,
            f"all {n_sub_checked}/{x['n_sub']} subs start fresh; "
            f"{len(bad)} start large; max first_out={max_first}",
        )
    )
    print(base("subagent share %", round(x["share"], 1), BASELINE["node2_share_pct"]))
    print(base("main_tok", x["main_tok"], BASELINE["node2_main_tok"]))
    print(base("sub_tok", x["sub_tok"], BASELINE["node2_sub_tok"]))
    print(f"        threads {x['n_main']} root / {x['n_sub']} sub")
    for fo, mxo, pm in x["sub_independence"][:4]:
        print(f"          sub first={fo:<6} max={mxo:<8} parent_max={pm}")

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

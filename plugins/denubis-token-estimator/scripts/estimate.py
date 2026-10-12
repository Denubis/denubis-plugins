#!/usr/bin/env python3
"""Token/word estimator — per project, rolled up from the directory (via the
.token-estimator mapper), optionally broken down by month.

Reuses the audited methodology in verify.py as the single source of truth
(origin dedup, machine-tag allow-lists, replay-aware Codex counters) and the mapper in
mapper.py for directory rollup. People-roots come from ~/.token-estimator (else the
target/local directory) — see verify.load_roots.

Usage:
  python3 estimate.py --dir .                 # project of a directory (cwd)
  python3 estimate.py --dir <path> --month    # ... broken down by month
  python3 estimate.py --dir <path> --start <ISO> --end <ISO>
  python3 estimate.py --person Jodie          # every project for a person
  python3 estimate.py --person Jodie --month  # ... with month rows
  python3 estimate.py --all                   # every person/project (rollup)
  python3 estimate.py --dir <path> --csv out.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mapper as M
import verify as V


def make_attr(roots):
    """Build mapper-aware attribution bound to a specific roots list."""
    aliases = M.load(roots)
    return lambda cwd: M.attribute(cwd, aliases, lambda c: V.attribute(c, roots))


_CODEX_MONTH = re.compile(r"rollout-(\d{4}-\d{2})")


# leaf key = (source, person, project, month)
#   -> [main_tok, sub_tok, human_words, pasted_words]
# human_words are the human's own authorship; pasted_words are text the human
# submitted but did not write (paste wrapper bodies, forwarded side-agent notes).
SLOTS = 4


def _blank():
    return [0] * SLOTS


def _remember_claude_user(human_by_uuid, record):
    uid = record.get("uuid")
    when = V.parse_timestamp(record.get("timestamp"))
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        blocks = [content]
    elif isinstance(content, list):
        blocks = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
    else:
        blocks = []
    previous = human_by_uuid.get(uid)
    if previous is None or (
        when is not None and (previous[0] is None or when < previous[0])
    ):
        human_by_uuid[uid] = (
            when,
            record.get("cwd"),
            record.get("timestamp"),
            blocks,
        )


def _add_claude_human_words(leaves, attr, human_by_uuid, start, end):
    for when, cwd, timestamp, blocks in human_by_uuid.values():
        if start is not None and not (when is not None and start <= when < end):
            continue
        person, project, _ = attr(cwd)
        month = (
            "(window)" if start is not None else (timestamp or "")[:7] or "(no-date)"
        )
        words = pasted_words = 0
        for text in blocks:
            if not text or not text.strip() or V.claude_machine_marker(text):
                continue
            original, pasted = V.split_pasted(text)
            words += len(original.split())
            pasted_words += len(pasted.split())
        if words or pasted_words:
            leaf = leaves[("claude", person, project, month)]
            leaf[2] += words
            leaf[3] += pasted_words


def collect_claude(leaves, attr, *, start=None, end=None):
    out_max = collections.defaultdict(int)
    in_main = collections.defaultdict(bool)
    cwd_atmax = {}
    month_atmax = {}
    first_main = {}
    first_sub = {}
    human_by_uuid = {}
    for fp in V.claude_files():
        is_sub = "/subagents/" in str(fp)
        try:
            fh = fp.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
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
                    is_main = not (is_sub or r.get("isSidechain") is True)
                    if is_main:
                        in_main[mid] = True
                    when = V.parse_timestamp(r.get("timestamp"))
                    origins = first_main if is_main else first_sub
                    if when is not None and (mid not in origins or when < origins[mid]):
                        origins[mid] = when
                    out = (m.get("usage") or {}).get("output_tokens") or 0
                    previous_cwd = cwd_atmax.get(mid)
                    if (
                        mid not in cwd_atmax
                        or out > out_max[mid]
                        or (
                            out == out_max[mid]
                            and previous_cwd is not None
                            and str(r.get("cwd")) < str(previous_cwd)
                        )
                    ):
                        out_max[mid] = out
                        cwd_atmax[mid] = r.get("cwd")
                        month_atmax[mid] = (r.get("timestamp") or "")[:7] or "(no-date)"
                elif t == "user" and not is_sub:
                    if V.claude_user_excluded(r):
                        continue
                    _remember_claude_user(human_by_uuid, r)
    _add_claude_human_words(leaves, attr, human_by_uuid, start, end)
    for mid, out in out_max.items():
        origin = first_main.get(mid) if in_main[mid] else first_sub.get(mid)
        if start is not None and not (origin is not None and start <= origin < end):
            continue
        person, project, _ = attr(cwd_atmax.get(mid))
        month = "(window)" if start is not None else month_atmax[mid]
        leaves[("claude", person, project, month)][0 if in_main[mid] else 1] += out


def collect_codex(leaves, attr, *, start=None, end=None):
    for thread in V.codex_threads():
        fp = Path(thread["file"])
        mm = _CODEX_MONTH.search(fp.name)
        month = "(window)" if start is not None else mm.group(1) if mm else "(no-date)"
        person, project, _ = attr(thread["cwd"])
        key = ("codex", person, project, month)
        output = (
            V.windowed_output(thread, start, end)
            if start is not None
            else thread["output_tokens"]
        )
        leaves[key][1 if thread["kind"] == "sub" else 0] += output
        if thread["kind"] == "main":
            leaves[key][2] += sum(
                len(text.split())
                for when, text in thread["user_texts"]
                if not V.codex_machine_marker(text)
                and (start is None or (when is not None and start <= when < end))
            )


def rollup(leaves, keep_month=False):
    """Collapse leaves to (person, project[, month]) totals."""
    agg = collections.defaultdict(_blank)
    for (_src, person, project, month), v in leaves.items():
        k = (person, project) + ((month,) if keep_month else ())
        for i in range(SLOTS):
            agg[k][i] += v[i]
    return agg


def fmt(n):
    return f"{n:,}"


def share(m, s):
    return (s / (m + s) * 100) if (m + s) else 0


def print_project(leaves, person, project, by_month):
    rows = rollup(leaves, keep_month=True)
    months = sorted(m for (pe, pr, m) in rows if pe == person and pr == project)
    tot = _blank()
    width = 82
    print(
        f"\n{'=' * width}\n{person} / {project}"
        f"{'  (by month)' if by_month else ''}\n{'=' * width}"
    )
    print(
        f"{'month':<12}{'main_tok':>14}{'sub_tok':>12}{'sub%':>6}"
        f"{'own_words':>12}{'pasted':>10}"
    )
    print("-" * width)
    for m in months:
        v = rows[(person, project, m)]
        for i in range(SLOTS):
            tot[i] += v[i]
        if by_month:
            print(
                f"{m:<12}{fmt(v[0]):>14}{fmt(v[1]):>12}"
                f"{share(v[0], v[1]):>5.0f}%{fmt(v[2]):>12}{fmt(v[3]):>10}"
            )
    print("-" * width)
    print(
        f"{'TOTAL':<12}{fmt(tot[0]):>14}{fmt(tot[1]):>12}"
        f"{share(tot[0], tot[1]):>5.0f}%{fmt(tot[2]):>12}{fmt(tot[3]):>10}"
    )
    print(
        f"\n  output tokens: {fmt(tot[0] + tot[1])} "
        f"({share(tot[0], tot[1]):.0f}% subagent)   "
        f"human words: {fmt(tot[2])} own + {fmt(tot[3])} pasted"
    )


def print_person(leaves, person, by_month):
    rows = rollup(leaves, keep_month=True)
    projects = sorted({pr for (pe, pr, m) in rows if pe == person})
    gt = _blank()
    print(f"\n{'=' * 72}\n{person} — all projects\n{'=' * 72}")
    print(
        f"{'project':<40}{'main_tok':>13}{'sub_tok':>11}{'sub%':>6}"
        f"{'own_words':>11}{'pasted':>9}"
    )
    for project in projects:
        months = sorted(m for (pe, pr, m) in rows if pe == person and pr == project)
        pt = _blank()
        for m in months:
            v = rows[(person, project, m)]
            for i in range(SLOTS):
                pt[i] += v[i]
        print(
            f"\n{project:<40}{fmt(pt[0]):>13}{fmt(pt[1]):>11}"
            f"{share(pt[0], pt[1]):>5.0f}%{fmt(pt[2]):>11}{fmt(pt[3]):>9}"
        )
        if by_month:
            for m in months:
                v = rows[(person, project, m)]
                print(
                    f"   {m:<37}{fmt(v[0]):>13}{fmt(v[1]):>11}"
                    f"{share(v[0], v[1]):>5.0f}%{fmt(v[2]):>11}{fmt(v[3]):>9}"
                )
        for i in range(SLOTS):
            gt[i] += pt[i]
    print(f"\n{'=' * 72}")
    print(
        f"{person} TOTAL: {fmt(gt[0] + gt[1])} output tokens "
        f"({share(gt[0], gt[1]):.0f}% subagent), "
        f"{fmt(gt[2])} own human words + {fmt(gt[3])} pasted"
    )


def write_csv(leaves, path):
    with Path(path).open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "source",
                "person",
                "project",
                "month",
                "main_tok",
                "sub_tok",
                "human_words",
                "pasted_words",
            ]
        )
        for (src, person, project, month), v in sorted(leaves.items()):
            w.writerow([src, person, project, month, *v[:SLOTS]])
    print(f"[csv] wrote {path}", file=sys.stderr)


def _window_timestamp(value):
    parsed = V.parse_timestamp(value)
    if parsed is None:
        raise argparse.ArgumentTypeError("must be an ISO 8601 timestamp")
    if parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must include a UTC offset or Z")
    return parsed


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument(
        "--dir", help="estimate the project this directory rolls up to (default: cwd)"
    )
    g.add_argument("--person")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--month", action="store_true", help="break down by month")
    ap.add_argument(
        "--start",
        type=_window_timestamp,
        help="inclusive ISO 8601 window start (requires --end)",
    )
    ap.add_argument(
        "--end",
        type=_window_timestamp,
        help="exclusive ISO 8601 window end (requires --start)",
    )
    ap.add_argument("--csv", dest="csv_out")
    args = ap.parse_args(argv)
    if (args.start is None) != (args.end is None):
        ap.error("--start and --end must be provided together")
    if args.start is not None and args.start >= args.end:
        ap.error("--start must be earlier than --end")
    if args.start is not None and args.month:
        ap.error("--month cannot be combined with an exact window")
    return args


def main(argv=None):
    args = parse_args(argv)

    # Roots: ~/.token-estimator if present, else the target/local directory. In --dir
    # mode the directory itself seeds the fallback root, so a config-less run still
    # attributes that tree correctly.
    target = args.dir if args.dir else (None if (args.person or args.all) else ".")
    roots = V.load_roots(target)
    attr = make_attr(roots)
    sys.stderr.write(f"roots: {roots}\n")
    if args.start is not None:
        sys.stderr.write(
            f"window: [{args.start.isoformat()}, {args.end.isoformat()})\n"
        )

    leaves = collections.defaultdict(_blank)
    sys.stderr.write("scanning Claude logs...\n")
    collect_claude(leaves, attr, start=args.start, end=args.end)
    sys.stderr.write("scanning Codex logs...\n")
    collect_codex(leaves, attr, start=args.start, end=args.end)

    if args.csv_out:
        write_csv(leaves, args.csv_out)

    if args.person:
        print_person(leaves, args.person, args.month)
    elif args.all:
        agg = rollup(leaves)
        for person, project in sorted(agg):
            m, s, w, p = agg[(person, project)]
            print(
                f"{person:<16}{project:<36}{fmt(m + s):>14} tok  "
                f"{fmt(w):>10} own words  {fmt(p):>9} pasted"
            )
    else:
        d = str(Path(args.dir or ".").resolve())
        person, project, _ = attr(d)
        print(f"(resolved {d}\n      -> {person} / {project})")
        print_project(leaves, person, project, args.month)


if __name__ == "__main__":
    main()

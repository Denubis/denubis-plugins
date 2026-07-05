#!/usr/bin/env python3
"""Token/word estimator — per project, rolled up from the directory (via the
.token-estimator mapper), optionally broken down by month.

Reuses the audited methodology in verify.py as the single source of truth
(origin dedup, machine-tag allow-lists, additive Codex subagents) and the mapper in
mapper.py for directory rollup. People-roots come from ~/.token-estimator (else the
target/local directory) — see verify.load_roots.

Usage:
  python3 estimate.py --dir .                 # project of a directory (cwd)
  python3 estimate.py --dir <path> --month    # ... broken down by month
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


# leaf key = (source, person, project, month) -> [main_tok, sub_tok, words]
def _blank():
    return [0, 0, 0]


def collect_claude(leaves, attr):
    out_max = collections.defaultdict(int)
    in_main = collections.defaultdict(bool)
    cwd_atmax = {}
    month_atmax = {}
    seen_uuid = set()
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
                    if not (is_sub or r.get("isSidechain") is True):
                        in_main[mid] = True
                    out = (m.get("usage") or {}).get("output_tokens") or 0
                    if mid not in cwd_atmax or out > out_max[mid]:
                        out_max[mid] = out
                        cwd_atmax[mid] = r.get("cwd")
                        month_atmax[mid] = (r.get("timestamp") or "")[:7] or "(no-date)"
                elif t == "user" and not is_sub:
                    if (
                        r.get("isSidechain") is True
                        or "toolUseResult" in r
                        or r.get("isMeta") is True
                    ):
                        continue
                    uid = r.get("uuid")
                    if uid in seen_uuid:
                        continue
                    seen_uuid.add(uid)
                    person, project, _ = attr(r.get("cwd"))
                    month = (r.get("timestamp") or "")[:7] or "(no-date)"
                    msg = r.get("message") or {}
                    content = msg.get("content")
                    blocks = (
                        [content]
                        if isinstance(content, str)
                        else [
                            b.get("text", "")
                            for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        ]
                        if isinstance(content, list)
                        else []
                    )
                    w = sum(
                        len(tx.split())
                        for tx in blocks
                        if tx and tx.strip() and V.lead_tag(tx) not in V.MACHINE_TAGS
                    )
                    if w:
                        leaves[("claude", person, project, month)][2] += w
    for mid, out in out_max.items():
        person, project, _ = attr(cwd_atmax.get(mid))
        leaves[("claude", person, project, month_atmax[mid])][
            0 if in_main[mid] else 1
        ] += out


def collect_codex(leaves, attr):
    for fp in V.codex_files():
        own = None
        seen = False
        kind = "main"
        mx = 0
        cwd = None
        utext = []
        mm = _CODEX_MONTH.search(fp.name)
        month = mm.group(1) if mm else "(no-date)"
        try:
            fh = fp.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                t = r.get("type")
                p = r.get("payload") or {}
                if t == "session_meta" and not seen:
                    own = p.get("id")
                    cwd = p.get("cwd")
                    kind = "sub" if isinstance(p.get("source"), dict) else "main"
                    seen = True
                elif t == "event_msg" and p.get("type") == "token_count":
                    o = ((p.get("info") or {}).get("total_token_usage") or {}).get(
                        "output_tokens"
                    )
                    if isinstance(o, (int, float)) and o > mx:
                        mx = int(o)
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
                        utext.append("\n".join(parts))
        if not own:
            continue
        person, project, _ = attr(cwd)
        key = ("codex", person, project, month)
        leaves[key][1 if kind == "sub" else 0] += mx
        if kind == "main":
            leaves[key][2] += sum(
                len(tx.split()) for tx in utext if not V.codex_machine_marker(tx)
            )


def rollup(leaves, keep_month=False):
    """Collapse leaves to (person, project[, month]) totals."""
    agg = collections.defaultdict(_blank)
    for (_src, person, project, month), v in leaves.items():
        k = (person, project) + ((month,) if keep_month else ())
        for i in range(3):
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
    print(
        f"\n{'=' * 72}\n{person} / {project}"
        f"{'  (by month)' if by_month else ''}\n{'=' * 72}"
    )
    print(f"{'month':<12}{'main_tok':>14}{'sub_tok':>12}{'sub%':>6}{'words':>12}")
    print("-" * 72)
    for m in months:
        v = rows[(person, project, m)]
        for i in range(3):
            tot[i] += v[i]
        if by_month:
            print(
                f"{m:<12}{fmt(v[0]):>14}{fmt(v[1]):>12}"
                f"{share(v[0], v[1]):>5.0f}%{fmt(v[2]):>12}"
            )
    print("-" * 72)
    print(
        f"{'TOTAL':<12}{fmt(tot[0]):>14}{fmt(tot[1]):>12}"
        f"{share(tot[0], tot[1]):>5.0f}%{fmt(tot[2]):>12}"
    )
    print(
        f"\n  output tokens: {fmt(tot[0] + tot[1])} "
        f"({share(tot[0], tot[1]):.0f}% subagent)   human words: {fmt(tot[2])}"
    )


def print_person(leaves, person, by_month):
    rows = rollup(leaves, keep_month=True)
    projects = sorted({pr for (pe, pr, m) in rows if pe == person})
    gt = _blank()
    print(f"\n{'=' * 72}\n{person} — all projects\n{'=' * 72}")
    for project in projects:
        months = sorted(m for (pe, pr, m) in rows if pe == person and pr == project)
        pt = _blank()
        for m in months:
            v = rows[(person, project, m)]
            for i in range(3):
                pt[i] += v[i]
        print(
            f"\n{project:<40}{fmt(pt[0]):>13}{fmt(pt[1]):>11}"
            f"{share(pt[0], pt[1]):>5.0f}%{fmt(pt[2]):>11}"
        )
        if by_month:
            for m in months:
                v = rows[(person, project, m)]
                print(
                    f"   {m:<37}{fmt(v[0]):>13}{fmt(v[1]):>11}"
                    f"{share(v[0], v[1]):>5.0f}%{fmt(v[2]):>11}"
                )
        for i in range(3):
            gt[i] += pt[i]
    print(f"\n{'=' * 72}")
    print(
        f"{person} TOTAL: {fmt(gt[0] + gt[1])} output tokens "
        f"({share(gt[0], gt[1]):.0f}% subagent), {fmt(gt[2])} human words"
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
            ]
        )
        for (src, person, project, month), v in sorted(leaves.items()):
            w.writerow([src, person, project, month, v[0], v[1], v[2]])
    print(f"[csv] wrote {path}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument(
        "--dir", help="estimate the project this directory rolls up to (default: cwd)"
    )
    g.add_argument("--person")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--month", action="store_true", help="break down by month")
    ap.add_argument("--csv", dest="csv_out")
    args = ap.parse_args()

    # Roots: ~/.token-estimator if present, else the target/local directory. In --dir
    # mode the directory itself seeds the fallback root, so a config-less run still
    # attributes that tree correctly.
    target = args.dir if args.dir else (None if (args.person or args.all) else ".")
    roots = V.load_roots(target)
    attr = make_attr(roots)
    sys.stderr.write(f"roots: {roots}\n")

    leaves = collections.defaultdict(_blank)
    sys.stderr.write("scanning Claude logs...\n")
    collect_claude(leaves, attr)
    sys.stderr.write("scanning Codex logs...\n")
    collect_codex(leaves, attr)

    if args.csv_out:
        write_csv(leaves, args.csv_out)

    if args.person:
        print_person(leaves, args.person, args.month)
    elif args.all:
        agg = rollup(leaves)
        for person, project in sorted(agg):
            m, s, w = agg[(person, project)]
            print(f"{person:<16}{project:<36}{fmt(m + s):>14} tok  {fmt(w):>10} words")
    else:
        d = str(Path(args.dir or ".").resolve())
        person, project, _ = attr(d)
        print(f"(resolved {d}\n      -> {person} / {project})")
        print_project(leaves, person, project, args.month)


if __name__ == "__main__":
    main()

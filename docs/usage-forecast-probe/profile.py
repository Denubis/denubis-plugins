import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Australia/Sydney")
root = Path("~/.claude/projects").expanduser()
out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("rows.tsv")
rows = []  # (ts, model, in, cc, cr, out, session)
seen = set()
for f in root.rglob("*.jsonl"):
    try:
        with f.open("rb") as fh:
            for line in fh:
                if b'"usage"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue  # a torn tail line is expected
                m = o.get("message") or {}
                u = m.get("usage")
                if not u or o.get("type") != "assistant":
                    continue
                rid = (m.get("id"), o.get("requestId"))
                key = (o.get("sessionId"), m.get("id"))
                if key in seen:
                    continue
                seen.add(key)
                ts = o.get("timestamp")
                if not ts:
                    continue
                rows.append(
                    (
                        ts,
                        m.get("model", ""),
                        u.get("input_tokens", 0),
                        u.get("cache_creation_input_tokens", 0),
                        u.get("cache_read_input_tokens", 0),
                        u.get("output_tokens", 0),
                        o.get("sessionId"),
                    )
                )
    except OSError:
        pass
print("messages", len(rows), file=sys.stderr)
with out_path.open("w") as out:
    for r in rows:
        out.write("\t".join(map(str, r)) + "\n")

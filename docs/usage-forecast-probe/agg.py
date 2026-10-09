import collections
import datetime as dt
import statistics as st
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Australia/Sydney")
rows = []
with Path("rows.tsv").open() as fh:
    rows_raw = [line.rstrip("\n").split("\t") for line in fh]
for ts, model, i, cc, cr, o, sid in rows_raw:
    t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(TZ)
    rows.append((t, model, int(i), int(cc), int(cr), int(o), sid))
rows.sort()
print("range", rows[0][0].date(), rows[-1][0].date())


# weighted cost proxy: input and cache_create at 1x, cache_read at 0.1x,
# output at 5x (approximate Anthropic price ratios)
def w(r):
    return r[2] + r[3] + 0.1 * r[4] + 5 * r[5]


# weekday x hour profile over last 12 weeks
cut = rows[-1][0] - dt.timedelta(weeks=12)
recent = [r for r in rows if r[0] >= cut]
prof = collections.defaultdict(float)
days = collections.defaultdict(set)
for r in recent:
    prof[(r[0].weekday(), r[0].hour)] += w(r)
    days[r[0].weekday()].add(r[0].date())
print("\nweekday x hour, mean weighted-token-units per hour (millions), last 12 weeks")
print("     " + " ".join(f"{h:>4}" for h in range(24)))
for d in range(7):
    n = max(1, len(days[d]))
    print(
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d],
        " ".join(f"{prof[(d, h)] / n / 1e6:4.1f}" for h in range(24)),
    )
# per-weekday totals
print(
    "\nper-weekday mean daily units (M):",
    {
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d]: round(
            sum(prof[(d, h)] for h in range(24)) / max(1, len(days[d])) / 1e6, 1
        )
        for d in range(7)
    },
)
# model mix recent
mm = collections.Counter()
for r in recent:
    mm[r[1]] += w(r)
tot = sum(mm.values())
print(
    "\nmodel mix (weighted) last 12 weeks:",
    {k: f"{v / tot:.0%}" for k, v in mm.most_common(8)},
)
# concurrency: distinct sessions active per 5-min bin
bins = collections.defaultdict(set)
cost = collections.defaultdict(float)
for r in recent:
    b = r[0].replace(minute=r[0].minute // 5 * 5, second=0, microsecond=0)
    bins[b].add(r[6])
    cost[b] += w(r)
byn = collections.defaultdict(list)
for b, s in bins.items():
    byn[min(len(s), 6)].append(cost[b])
print(
    "\nbusy sessions in a 5-min bin -> median & mean units per bin (M), count of bins"
)
for n in sorted(byn):
    print(
        n,
        round(st.median(byn[n]) / 1e6, 2),
        round(st.mean(byn[n]) / 1e6, 2),
        len(byn[n]),
    )
# context size effect: cost per message vs context (cache_read+input+cache_create)
ctx = collections.defaultdict(list)
for r in recent:
    c = r[2] + r[3] + r[4]
    k = min(c // 25000, 8)
    ctx[k].append(w(r))
print("\ncontext bucket (x25k tokens) -> mean units per message (k), n")
for k in sorted(ctx):
    print(k, round(st.mean(ctx[k]) / 1e3, 1), len(ctx[k]))
# weekly totals vs Fri 16:00 reset
wk = collections.defaultdict(float)
wkf = collections.defaultdict(float)
for r in rows:
    t = r[0]
    shift = t - dt.timedelta(hours=16)
    # window index: weeks since a Friday
    wd = (shift.weekday() - 4) % 7
    wstart = (shift - dt.timedelta(days=wd)).date()
    wk[wstart] += w(r)
    if "fable" in r[1] or "mythos" in r[1]:
        wkf[wstart] += w(r)
print(
    "\nweighted units per weekly window (Fri16:00 start), last 10, M, and fable share"
)
for k in sorted(wk)[-10:]:
    print(k, round(wk[k] / 1e6, 1), f"{wkf[k] / wk[k]:.0%}" if wk[k] else "")

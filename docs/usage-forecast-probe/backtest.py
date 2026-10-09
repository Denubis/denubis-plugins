import collections
import datetime as dt
import statistics as st
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Australia/Sydney")
rows = []
with Path("rows.tsv").open() as fh:
    rows_raw = [line.rstrip("\n").split("\t") for line in fh]
for ts, _model, i, cc, cr, o, _sid in rows_raw:
    t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(TZ)
    rows.append((t, int(i) + int(cc) + 0.1 * int(cr) + 5 * int(o)))
rows.sort()


# bin into hours, keyed by window start (Fri 16:00 local)
def wstart(t):
    s = t - dt.timedelta(hours=16)
    wd = (s.weekday() - 4) % 7
    d = (s - dt.timedelta(days=wd)).date()
    return dt.datetime(d.year, d.month, d.day, 16, tzinfo=TZ)


hours = collections.defaultdict(float)
for t, c in rows:
    hours[t.replace(minute=0, second=0, microsecond=0)] += c
windows = collections.defaultdict(lambda: [0.0] * 168)
for h, c in hours.items():
    ws = wstart(h)
    idx = int((h - ws).total_seconds() // 3600)
    if 0 <= idx < 168:
        windows[ws][idx] += c
keys = sorted(windows)
keys = [
    k
    for k in keys
    if k >= dt.datetime(2026, 6, 1, tzinfo=TZ) and sum(windows[k]) > 50e6
]
print("windows evaluated:", len(keys), keys[0].date(), keys[-1].date())


# walk-forward: profile from prior 8 windows (median per hour-of-window),
# evaluate on window k
def forecast_eval(method):
    errs = collections.defaultdict(list)
    for i, k in enumerate(keys):
        prior = [windows[x] for x in keys[max(0, i - 8) : i]]
        if len(prior) < 3:
            continue
        prof = [st.median(p[h] for p in prior) for h in range(168)]
        cum = windows[k]
        total = sum(cum)
        for h in range(12, 168, 12):  # every 12h into the window
            used = sum(cum[:h])
            rem_true = total - used
            if method == "linear":
                rem = used / h * (168 - h)
            elif method == "profile":
                # expected remaining from profile, scaled by this week's
                # intensity so far (shrunk toward 1)
                exp_sofar = sum(prof[:h])
                exp_rem = sum(prof[h:])
                ratio = (
                    (used + 0.2 * exp_sofar) / (exp_sofar + 0.2 * exp_sofar)
                    if exp_sofar > 0
                    else 1.0
                )
                rem = exp_rem * ratio
            elif method == "profile_raw":
                rem = sum(prof[h:])
            errs[h].append(abs(rem - rem_true) / max(total, 1))
    return errs


for m in ("linear", "profile_raw", "profile"):
    e = forecast_eval(m)
    print(
        f"\n{m}: mean abs error of remaining-forecast as % of window total,"
        " by hours into window"
    )
    print(
        "  "
        + "  ".join(
            f"{h:>3}h:{st.mean(e[h]) * 100:4.0f}%"
            for h in sorted(e)
            if h % 24 == 0 or h == 12
        )
    )


def ev2(shrink, blend_from):
    errs = collections.defaultdict(list)
    for i, k in enumerate(keys):
        prior = [windows[x] for x in keys[max(0, i - 8) : i]]
        if len(prior) < 3:
            continue
        prof = [st.median(p[h] for p in prior) for h in range(168)]
        cum = windows[k]
        total = sum(cum)
        for h in range(12, 168, 12):
            used = sum(cum[:h])
            rem_true = total - used
            es = sum(prof[:h])
            er = sum(prof[h:])
            ratio = (used + shrink * es) / (es + shrink * es) if es > 0 else 1.0
            rp = er * ratio
            rl = used / h * (168 - h)
            wgt = min(1, max(0, (h - blend_from) / (168 - blend_from)))
            rem = (1 - wgt) * rp + wgt * rl
            errs[h].append(abs(rem - rem_true) / max(total, 1))
    return errs


print("\nshrink / blend_from -> error at 24h,48h,96h,144h")
for shrink in (1.0, 3.0, 10.0, 1e9):
    for bf in (72, 120, 168):
        e = ev2(shrink, bf)
        print(
            f"  shrink={shrink:<6} blend_from={bf:<4}",
            "  ".join(f"{h}h:{st.mean(e[h]) * 100:3.0f}%" for h in (24, 48, 96, 144)),
        )

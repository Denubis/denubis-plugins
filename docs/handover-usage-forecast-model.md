# Handover: forecasting weekly quota exhaustion from covariates

Written 2026-10-09 by the dispatching Claude Code session (Fable 5.1) after a first-cut
probe of Brian's transcript history. Nothing here is implemented in the status line.
Human rulings are marked **human**; everything else is **observed** from the probe
scripts in `docs/usage-forecast-probe/` (first run from `/tmp/usage-fit/`) or
**proposed**.

## 0. Human rulings (this session)

- "I don't need that query to be aggressive, once every 5 minutes is fine." Poll the
  usage endpoint at most every five minutes.
- Consumption is not linear. Trends vary by time of day, day of week, number of
  sessions running, "etc."; the model must "manage all these covariates and generally
  look at trends over the last whole-number-of-windows, because there are many things
  that impact these trends."
- The weekly reset is Friday 16:00 Australia/Sydney (observed: `resets_at`
  2026-10-09T05:00Z). The five-hour window is not of interest.

## 1. Data available (observed)

- `~/.claude/projects/**/*.jsonl`: 350,523 assistant messages with `usage` from
  2026-01-12 to 2026-10-09, each with timestamp, model, input, cache-create, cache-read
  and output tokens, and session id. Extracted to `/tmp/usage-fit/rows.tsv` by
  `profile.py`. Subagent transcripts are included; they carry their own session ids.
- Official percentages: the usage endpoint's `limits[]` (see
  `docs/handover-statusline-mod.md` §1a) gives weekly-all and weekly-Fable percent and
  `resets_at`. Historical percent samples: none kept yet except what
  `workflow_statusline` appended to its cache file (not inspected). The token-to-percent
  mapping is unknown and must be calibrated from paired samples once polling starts.

Cost proxy used in the probe (proposed, not calibrated): `input + cache_create +
0.1*cache_read + 5*output`, weighted equally across models. Replace with the fitted
mapping once percent samples exist.

## 2. What the probe showed (observed, last 12 weeks unless stated)

- **Time of day:** nothing before 07:00; peak 12:00 to 18:00; tail to 22:00. Hourly
  means range from 0 to 8.1M units.
- **Day of week:** mean daily units Mon 58, Tue 44, Wed 43, Thu 40, Fri 38, Sat 53,
  Sun 25 (millions). Not uniform; Saturday is a heavy day.
- **Concurrency:** units per 5-minute bin rise roughly linearly with the number of
  sessions active in that bin: medians 0.16, 0.41, 0.71, 0.87, 1.26, 1.76M for 1 to 6+
  sessions. Approximately additive per session.
- **Context size:** mean units per message by context bucket (25k steps): 4.9k at <25k,
  about 20 to 22k at 25k to 125k, 27 to 30k at 150k to 200k, 48.3k at >200k. Half of all
  messages sit in the >200k bucket. Context is the single largest per-message driver.
- **Model mix:** Opus 5 43%, Fable 5.1 15%, Opus 5.5 14%, Fable 5 12%, Sonnet 5 9%.
- **Between-window variance:** weighted units per weekly window (Fri 16:00 start) over
  the last ten windows range from 40M to 423M. Fable's share ranges 8% to 53%. This
  variance is the floor on any forecast made at the start of a window.

## 3. Backtest of two naive forecasts (observed, 17 windows since June, walk-forward)

Mean absolute error of the forecast of *remaining* consumption, as a share of the
window's final total, by hours into the window:

| hours in | linear pace | weekday-hour profile (median of prior 8 windows) |
| --- | --- | --- |
| 12 | 79% | 29% |
| 24 | 72% | 29% |
| 48 | 57% | 26% |
| 72 | 39% | 24% |
| 96 | 31% | 22% |
| 120 | 18% | 19% |
| 144 | 11% | 12% |

Scaling the profile by the current window's intensity-so-far made it worse early
(152% at 12h) because 12 hours of a window is too little to estimate intensity. The
profile beats linear until about day five; after that both are within the noise.
Script: `docs/usage-forecast-probe/backtest.py` (its last experiment has a division-by-zero at
`blend_from=168`; harmless, fix or drop).

Conclusion: covariates carry large signal, linear pace is the wrong baseline for the
first four days, and a hand-tuned profile is not the answer because it cannot absorb
concurrency, context, model mix or behaviour under quota.

## 4. The model to build (proposed)

**Unit of observation:** one 5-minute bin (or one hour; test both) within a weekly
window. Response: cost units consumed in the bin (later: official percent increment,
once calibrated). Zero-inflated, non-negative.

**Covariates, all derivable locally:**

1. Weekday × hour of day (168 levels, or a smooth: cyclic splines on hour, by weekday).
2. Hours since window reset (position in the window; today collinear with weekday,
   kept separate in case the reset moves).
3. Number of sessions active in the bin, and active in the previous hour.
4. Mean and max context size of active sessions (tokens), from the transcripts.
5. Model mix of active sessions (share of Fable, Opus, Sonnet), since pools differ.
6. Percent remaining in the window at the bin (behavioural feedback: Brian slows or
   switches models near the limit). Only available once percent samples are logged;
   until then use cumulative cost-so-far as a proxy.
7. Autonomous-run flag: whether a workflow, loop, or Codex supervisor was active
   (bursty, machine-paced). Derivable from tool names in the transcripts.
8. Window index (trend across windows), as a slowly varying term.

**Form:** a Tweedie or negative-binomial GLM with log link (multiplicative effects,
handles zeros), or gradient-boosted trees with quantile objectives if interactions
matter more than interpretability. Fit on the last K *complete* windows (K = 8 to 12;
test), refit each window. Produce the forecast of remaining consumption as the sum of
predicted bin means from now to reset, with covariates for future bins taken from the
profile (sessions, context) and the current state for the next one to two hours.

**Output:** median and 10th/90th quantiles of time-to-100%, or "will not reach 100%
before reset at the 90th quantile". Display the quantile range, never a point.

**Evaluation:** the same walk-forward backtest as §3, reporting error at 12h, 24h,
48h, 96h, plus calibration of the quantile band (does the 10 to 90 band contain the
truth 80% of the time). The model must beat the §3 profile at every horizon or it is not
worth the complexity.

**Calibration to percent:** once five-minute percent samples accumulate, regress
percent increments on cost units by model to recover per-model weights, then refit the
response in percent. Until then all forecasts are in cost units and the "100%" line is
unknown.

## 5. Not checked

- Whether `workflow_statusline`'s cache holds enough historical percent samples to
  calibrate now.
- Codex usage: not in these transcripts and not in the Claude quota.
- Whether subagent transcripts double-count against the parent in the concurrency
  covariate (probe treated each session id as one session).
- Price-ratio weights in the cost proxy.

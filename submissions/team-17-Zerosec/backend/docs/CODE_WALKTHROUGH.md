# Code walkthrough: how to explain this project

## The 30-second pitch

Fixed rules like "alert if spend moves 30%" fail in both directions. Small campaigns trip them by chance every day, and big campaigns can drift 10% without ever crossing them. So we judge **each campaign against its own recent behaviour**, and we use the right noise model for each kind of metric.

Alerts then go through an alert manager that does four things:
- groups everything that happened to a campaign on one day into one finding
- recognises market-wide (seasonal) moves
- suppresses repeats
- re-notifies only when things get worse or come back

On the synthetic data, a naive ±30% rule would fire **1,103** alerts. We fire **64**, we catch all 4 seeded incidents on day 0, and every immediate page was a real incident. We also report our weak spot honestly: 24 digest-level false positives.

## Walk through the pipeline (in this order)

Open `app/services/pipeline.py`, function `analyze_load_result`. It is the whole program in about 20 lines. Then go stage by stage.

### 1. `data_loader.py`: getting trustworthy data in
- **Key function:** `normalize_frame`. It runs one helper per rule: `_normalize_headers`, `_apply_aliases`, `_parse_dates`, `_parse_numeric`, `_handle_duplicates`, `_fill_missing_days`.
- **Aliases.** Real exports say "Cost" or "Conv.", so `COLUMN_ALIASES` maps them to canonical names. We don't reject a file because of naming.
- **Never silently fix data.** A bad number becomes *missing*, not 0, because 0 conversions would look like a tracking break. Every fix produces a warning.
- **Missing days** become gaps that are not scored, so a missing export is never mistaken for a collapse.

### 2. `features.py`: ratios with a low-volume guard
- **What it does.** Computes CTR, CVR, CPC, CPA and ROAS, but only when the denominator is big enough (`MIN_DENOMINATOR`).
- **Why the guard.** A CVR computed from 3 clicks is noise. This also means a zero denominator can never produce infinity.

### 3. `detector.py`: the core idea (spend the most time here)
- **`rolling_baseline`.** For every day, it builds a row of the previous 28 days and takes the **median** (the expected value) and the **MAD** (the campaign's own volatility). Medians are robust: one weird day in the history doesn't move them.
- **`values.shift(1)`.** This is the no-leakage guarantee: a day is only ever compared with days before it.
- **Money and ratio metrics.** The score is (observed − median) / volatility, passed through `t_to_z`. The correction exists because the volatility is estimated from only ~28 days. Without it we got about 7× more false alarms on perfectly stable data. A test checks this rate.
- **Count metrics: `poisson_z`.** For counts, the right question is: "if conversions arrive randomly at 18 a day, how unlikely is seeing 2?" That's the Poisson tail, about 3 in a million, expressed as a z of about −4.5. If a campaign is naturally noisier than pure randomness, we widen the band in proportion (overdispersion).
  - This is **the answer to the problem statement**: 2 → 0 conversions on a tiny campaign is unremarkable (z ≈ −1), while 2,000 → 1,800 on a big campaign is alarming (z ≈ −4.5).
- **Two passes (`score_series`).** Anomalies found in pass 1 are removed from the history for pass 2. Otherwise a 2-week outage fills the 28-day window and starts to look normal. A permanent change, such as a bid strategy, still becomes the new normal, because pass 1 stops flagging it once it fills the window.
- **`classify_severity`.** Severity depends on the score, plus a rule that a volume metric collapsing ≥90% is critical and dropping ≥50% is at least high. Breakages show up as drops.

### 4. `diagnosis.py`: making alerts readable
- **`RULES`** is an ordered table where the first match wins. For example: conversions down but clicks normal means a **possible tracking issue**, and spend down with impressions down means a **possible budget or delivery problem**.
- **`describe_anomaly`** builds the sentence from measured numbers only: observed, baseline, normal range, % change.
- **Wording.** Causes are always "may indicate …", followed by a concrete first check. We never claim a confirmed root cause; a test enforces this.

### 5. `alert_manager.py`: alert fatigue (the second key idea)
- **`build_findings`.** Removes duplicates, then groups all anomalies for one campaign-day into one finding. When conversions, revenue, CVR, CPA and ROAS all move together, that's one finding, not five.
- **`find_portfolio_shifts`.** If ≥50% of the portfolio (at least 5 campaigns) moved the same metric more than 15% the same way that day, it's a market or seasonal move. It goes to the digest as `seasonality`. Exception: a campaign that moved more than 2× the portfolio's typical move is still its own problem (a −98% outage on a day everyone dipped 15%).
- **`manage_alerts`** is one loop with three branches:
  1. **Nothing open, or recovered** (at least 3 quiet days since the last finding) → `new` or `reopened` → notify.
  2. **Inside the cooldown and worse** → `escalated` → notify. The cooldown never hides a worsening problem.
  3. **Inside the cooldown, not worse** → `suppressed` → no notification, but kept as evidence.
- **Routing.** High or critical incidents are sent immediately. Everything else goes to the daily digest.
- **`summarize`.** The counts reconcile exactly; a test checks this.

### 6. `evaluation.py`: honest scoring
- **Incidents.** An incident is a run of labeled days. An alert is a true positive if it is for the same campaign and dated between the incident's start and its end + 2 days.
- **What we report.** Precision, recall, F1, precision of *immediate* alerts, every miss, every false-positive alert ID, and how many alerts the naive ±30% rule would have fired.
- **No labels, no invented numbers.** Without labels everything is `null` with a reason.

## Likely judge questions

**Why median/MAD instead of mean/standard deviation?**
A single outlier, such as yesterday's incident, drags the mean and inflates the standard deviation, which then hides the next incident. Median and MAD barely move. We also remove flagged days from the history (the two-pass approach) for the same reason.

**How do you stay quiet on tiny campaigns?**
Three mechanisms:
- Count metrics use a Poisson model, so a 2-conversions-a-day campaign needs a really unusual count before it alerts.
- Ratios aren't computed on tiny denominators.
- Moves under 5% are never flagged.

**How do you catch a 10% drift on a big campaign?**
Big campaigns have small relative noise. At 2,000 conversions a day, the random wobble is about ±45 (2%), so a 200-conversion drop is about 4.5 standard deviations. The band comes from the campaign's own history, not a global percentage.

**How do you know something is seasonality and not a breakage?**
A breakage hits one campaign; a seasonal or market move hits most of them at once, by a similar amount. We check how many campaigns moved the same way on the same day, and how far this campaign moved compared with them.

**What is the "score"?**
It is a z-score-like number: how far today is from the campaign's own recent median, measured in its own typical variation, with small-sample and Poisson corrections. It is a heuristic for ranking and thresholding. **It is not a probability.**

**What did you miss, and what are your false positives?**
- **Misses:** on the synthetic data, recall is 4 of 4.
- **False positives:** 24 medium-severity digest alerts that don't match a label, mostly genuine random outliers in the generator. Immediate pages were 4 of 4 correct.
- **Under-routed incident:** the bid-strategy change was caught on day 0 but sent to the digest instead of paging.
- **Tuning disclosure:** we tuned on this same data, which we disclose in the response.

**What happens when the official dataset arrives?**
Drop it in `data/official/` and run `python -m app.cli data\official\<file>.csv`. Headers are mapped automatically. If it has a label column (`is_incident`, `is_anomaly` or `label`), precision and recall are computed. The API test suite also picks it up automatically.

**What would you do with more time?**
- Day-of-week baselines, to remove weekend noise.
- Persistence (SQLite) so cooldowns span uploads.
- A feedback loop: when users mute or dismiss an alert type, learn from it.
- Per-metric thresholds tuned on held-out data.
- Paging on CPA/ROAS shifts above a business-defined cost impact.

## Demo script (about 3 minutes)

1. Run `python -m app.cli data\demo_campaigns.csv`. Point at 64 vs 1,103 alerts, 4 of 4 incidents caught, and the honest precision line.
2. Open http://127.0.0.1:8000/docs and run `POST /api/analyze/demo`. Show the C05 alert: the tracking explanation with real numbers, and the first diagnostic step.
3. Show C12: one `delivery_drop` alert with about 11 suppressed repeats. That is the cooldown keeping the channel quiet without hiding evidence.
4. Show a `portfolio_shift` alert from late May: the seasonal surge went to the digest, not a page.
5. Open `detector.py` → `poisson_z` and `rolling_baseline`, then `alert_manager.py` → `manage_alerts`. Those are the two core ideas.

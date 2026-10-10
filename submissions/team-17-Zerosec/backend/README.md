# PS-04 — Campaign Anomaly Alerting Without Alert Fatigue (backend)

A FastAPI backend that reads daily campaign metrics from a CSV and flags genuine anomalies. Each campaign is judged against **its own** recent history, not a global ±30% rule. Every alert comes with a plain-English explanation and a first diagnostic step. Repeats are grouped and suppressed so people don't mute the channel. The backend also reports how many alerts it fired and how they score against the seeded incidents, including its own false-positive rate.

> The bundled `data/demo_campaigns.csv` is **SYNTHETIC** (see `data/README.md`). It is not the official hackathon data. Every result below comes from that synthetic file.

## Results on the SYNTHETIC demo data

This is real output from `python -m app.cli data/demo_campaigns.csv`:

```
Analyzed 20 campaigns, 3600 records, 2026-01-01 to 2026-06-29
Total alerts fired over 180 days: 64 (4 immediate, 60 digest)
Anomalies detected: 337 / grouped: 178 / suppressed: 95 / escalated: 7 / reopened: 14
Alert episodes: 57 (28 routed as seasonality)
Precision / Recall / F1: 17.2% / 100.0% / 29.4% (5 of 29 incident alerts matched; 4 of 4 incidents caught)
Precision of immediate alerts: 100.0% (4 immediate incident alerts)
  caught: C03 bid_strategy_change 2026-04-15..2026-04-21 (first alert 2026-04-15, +0 days)
  caught: C05 tracking_break 2026-02-20..2026-02-26 (first alert 2026-02-20, +0 days)
  caught: C09 spend_spike 2026-05-08..2026-05-09 (first alert 2026-05-08, +0 days)
  caught: C12 budget_exhausted 2026-03-19..2026-03-31 (first alert 2026-03-19, +0 days)
Naive ±30% day-over-day rule would have fired: 1103 alerts (precision 1.5%, recall 75.0%)
```

**How to read this:**
- **Alert volume.** We sent 64 notifications over 180 days. The fixed ±30% rule would have sent 1,103 and still missed one of the four incidents.
- **Recall.** All 4 seeded incidents were caught on their first day.
- **Immediate alerts.** All 4 pages (immediate notifications) were real incidents.
- **Overall false positives.** 24 of the 29 incident-category alerts did not match a seeded incident, so overall precision is 17.2%. Almost all of these went to the **daily digest** at medium severity. Most are genuine statistical outliers in the synthetic generator's random noise (for example a 4σ revenue day), but they are false positives against the labels, and we report them as such.
- **Bid strategy change.** It was caught on day 0 but routed to the digest rather than paged: CPC rose 58% with a score of about 4.7, which is medium severity.
- **Seasonal shift (not an incident).** It produced 0 immediate alerts. Its alerts were routed as `seasonality` to the digest.
- **Tuning disclosure.** The thresholds and two rule changes were chosen while looking at this same dataset, so these numbers are optimistic. They are a sanity check, not an out-of-sample result. The full matching rule is in the API response under `evaluation.matching_rule`.

## Architecture

```
CSV upload ──► data_loader ──► features ──► detector ──► alert_manager ──► evaluation ──► JSON response
              (validate,       (CTR, CVR,   (per-campaign  (group by day,    (precision,
               aliases,         CPC, CPA,    rolling        seasonality,      recall,
               warnings)        ROAS)        baselines)     cooldown,         naive ±30%
                                                            escalation)       baseline)
                               diagnosis.py: alert type + plain-English explanation + first check
```

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, CORS |
| `app/api/routes.py` | HTTP endpoints (thin) |
| `app/schemas.py` | Pydantic response models: the frontend contract |
| `app/services/data_loader.py` | CSV → clean daily frame + data-quality warnings |
| `app/services/features.py` | Derived ratios with a low-volume guard |
| `app/services/detector.py` | Per-campaign anomaly scoring |
| `app/services/diagnosis.py` | Pattern rules → alert type, explanation, diagnostic steps |
| `app/services/alert_manager.py` | Grouping, seasonality, cooldown, escalation, reopen, routing |
| `app/services/evaluation.py` | Precision/recall against labels + naive baseline |
| `app/services/pipeline.py` | Runs the stages in order; shared by the API and CLI |
| `app/cli.py` | One-command text report |
| `scripts/generate_demo_data.py` | Deterministic SYNTHETIC dataset |

There is no database: each request is analyzed from scratch and gives the same result every time. See `docs/CODE_WALKTHROUGH.md` for a module-by-module explanation and likely judge questions.

## Setup (Windows PowerShell)

Prerequisites: Python 3.11 or newer (tested on 3.14).

```powershell
cd D:\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the API:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Interactive docs: http://127.0.0.1:8000/docs
- Base URL for the frontend: `http://127.0.0.1:8000/api`

Command-line report (the problem statement's minimum bar):

```powershell
python -m app.cli data\demo_campaigns.csv
python -m app.cli path\to\official.csv --cooldown-days 3 --json result.json
```

Run tests:

```powershell
python -m pytest -v
```

Current result: **91 passed, 1 skipped**. The skipped test runs automatically once a CSV is placed in `data/official/`.

## Endpoints

| Method & path | What it does |
|---|---|
| `GET /api/health` | `{"status":"ok","app":"PS-04 Campaign Anomaly Alerting","version":"0.1.0"}` |
| `POST /api/analyze` | Multipart upload, field name **`file`** (a `.csv`). Returns `AnalysisResponse`. |
| `POST /api/analyze/demo` | Same response for the bundled SYNTHETIC dataset (no upload). |
| `GET /api/demo-data?limit=50` | Sample rows of the demo CSV, with `synthetic: true` and a notice. |

Optional query parameters for both analyze endpoints:

| Param | Default | Range | Meaning |
|---|---|---|---|
| `window_days` | 28 | 7–90 | Past days used for each baseline |
| `min_history` | 14 | 5–60 | Valid past days required before a day is scored |
| `z_threshold` | 3.5 | 2–10 | Sensitivity: lower means more alerts |
| `cooldown_days` | 3 | 0–30 | Quiet days before an alert counts as recovered |

Status codes:
- **400**: not a `.csv`, or the file is empty
- **413**: file too large (`MAX_UPLOAD_MB`, default 10)
- **422**: validation error (missing columns, no valid rows, more rows than `MAX_ROWS` (default 200,000), bad parameters). The response has `{"detail": "..."}`.

Example requests:

```powershell
curl.exe -F "file=@data/demo_campaigns.csv" "http://127.0.0.1:8000/api/analyze?cooldown_days=3"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/analyze" -Form @{ file = Get-Item data\demo_campaigns.csv }
```

## Expected CSV schema

**Required:** a campaign column, a date column and at least one metric. Header names are matched case-insensitively, ignoring punctuation.

| Canonical | Accepted header names |
|---|---|
| `campaign_id` | campaign_id, campaign, campaignid (falls back to campaign_name) |
| `date` | date, day, report_date, ds, timestamp |
| `impressions` | impressions, impr, imps |
| `clicks` | clicks |
| `spend` | spend, cost, amount_spent, ad_spend |
| `conversions` | conversions, conv, convs, purchases, results |
| `revenue` | revenue, conversion_value, conv_value, purchase_value, sales |
| `is_incident` (optional label) | is_incident, is_anomaly, anomaly, label, incident |
| `incident_type` (optional) | incident_type, anomaly_type |

Data-handling rules. Each of these produces a warning in `warnings`:
- **Numbers.** `"$1,234.50"` and `"1,200"` are parsed as numbers. Non-numeric or negative values become missing; they are never treated as 0.
- **Dates.** Rows with an invalid or missing date or campaign are dropped.
- **Duplicates.** Exact duplicate rows are dropped. Remaining rows for the same campaign and date are **summed**, on the assumption that they are a breakdown such as ad-group rows.
- **Missing days.** Missing days become gaps. They are not scored and do not count as history.
- **File format.** A UTF-8 BOM and `;` delimiters (common in Excel exports) are supported. In a `;` file, `1.234,50` is read as 1234.5 (decimal comma), with a warning. Campaign IDs stay strings, so `007` is not the same as `7`. When a file has both `Campaign` and `Campaign ID` (as Google Ads exports do), the ID is the key and `Campaign` is the name.
- **Date formats.** Non-ISO dates are tried both month-first and day-first, and the interpretation that parses more rows into a tighter range wins (day-first adds a warning). Timezone offsets are dropped, keeping each row's local calendar date.
- **Derived ratios.** These are only computed when the denominator is large enough: CTR needs ≥500 impressions, CVR and CPC need ≥30 clicks, CPA needs ≥3 conversions, and ROAS needs ≥20 spend.

## How detection works

For every campaign and every metric, each day is compared with the **median of that campaign's previous 28 days**. Only past days are used, so there is no future leakage, and at least 14 valid past days are required.

- **Money and ratio metrics** (spend, revenue, CTR, CVR, CPC, CPA, ROAS). The band width is the campaign's own volatility, measured with the median absolute deviation (MAD). MAD is robust: one bad day in the history barely moves it. Because that volatility is estimated from only a few weeks, a Student-t correction converts the raw deviation into an equally surprising z-score. Without it, small samples produce too many false alarms; in tests on stable series the false-positive rate fell from 0.70% to under 0.1% per metric-day.
- **Count metrics** (impressions, clicks, conversions). We ask how surprising the count would be if events arrived at random at the baseline rate (a Poisson tail), widened if this campaign is naturally noisier than that. This is why a campaign with 2 conversions a day isn't paged when it gets 0, but a campaign with 2,000 a day is flagged when it drops 10%.
- **Two passes.** Days flagged in pass 1 are removed from the history used in pass 2, so an ongoing outage can't make "broken" look normal. A permanent change, such as a new bid strategy, still becomes the new normal after a few weeks.
- **Flagging.** A day is flagged when |score| ≥ 3.5 and it moved at least 5% from baseline.
- **Severity:**
  - **critical:** |score| ≥ 10, or a volume metric fell ≥ 90%
  - **high:** |score| ≥ 6, or a volume metric fell ≥ 50%
  - **medium:** anything else that was flagged
- **The score** is a heuristic, z-score-like number. **It is not a probability.**

## How grouping and suppression work

1. **Duplicates.** The same campaign, date and metric twice counts once.
2. **Grouping.** All anomalies for one campaign on one day become one **finding**. The strongest is the primary; the rest are related metrics (`grouped_alerts`).
3. **Seasonality.** If at least 5 campaigns were scored that day and at least half of them moved the same metric more than 15% in the same direction, the finding is a **portfolio shift** (`category: "seasonality"`). It always goes to the digest. The exception is a campaign that moved more than twice the portfolio's typical move; that stays an incident, so a −98% outage on a day when everyone dipped 15% is still flagged.
4. **Episodes.** Findings with the same campaign and alert type form one **alert**:
   - **`new`:** the first finding opens the alert and sends a notification.
   - **`suppressed`:** a repeat within the cooldown (3 days) is kept as evidence but not notified.
   - **`escalated`:** a repeat with higher severity is notified again.
   - **`reopened`:** a finding that comes after at least 3 quiet days (more than `cooldown_days` since the last finding) is a new notification, linked to the old alert via `reopened_from`.
5. **Routing.** Incidents with high or critical severity are sent **immediately**. Everything else goes to the **digest**.

The counts always reconcile:
- `anomalies_detected = duplicates_removed + findings + grouped_alerts`
- `findings = new + reopened + escalated + suppressed`
- `notifications_sent = new + reopened + escalated = immediate + digest`

Suppression never hides evidence: every finding stays in `alert.occurrences`.

## Frontend contract

- Base URL: `http://127.0.0.1:8000/api`. Upload with `FormData` and the field name **`file`**. Settings go in the query string.
- CORS allows `http://localhost:5173` and `http://127.0.0.1:5173` by default. Override with an environment variable, for example `$env:CORS_ORIGINS="http://localhost:3000"`.

```js
const fd = new FormData();
fd.append("file", fileInput.files[0]);
const res = await fetch("http://127.0.0.1:8000/api/analyze?cooldown_days=3", { method: "POST", body: fd });
const data = await res.json(); // on error: { detail: "..." }
```

Response shape (abbreviated, real values from the demo):

```jsonc
{
  "summary": { "campaigns_analyzed": 20, "records_analyzed": 3600, "input_rows": 3600,
               "date_start": "2026-01-01", "date_end": "2026-06-29", "days_covered": 180,
               "anomalies_detected": 337, "duplicates_removed": 0, "findings": 159, "grouped_alerts": 178,
               "new_alerts": 43, "reopened_alerts": 14, "escalated_alerts": 7, "suppressed_alerts": 95,
               "notifications_sent": 64, "immediate_notifications": 4, "digest_notifications": 60,
               "alerts_total": 57 },
  "config": { "window_days": 28, "min_history": 14, "z_threshold": 3.5, "cooldown_days": 3, "...": "..." },
  "metrics_analyzed": ["impressions","clicks","spend","conversions","revenue","ctr","cvr","cpc","cpa","roas"],
  "alerts": [{
    "alert_id": "C05:tracking_issue:2026-02-20", "campaign_id": "C05", "campaign_name": "Campaign 05 (social)",
    "alert_type": "tracking_issue",   // tracking_issue | delivery_drop | cost_efficiency_shift | spend_spike | volume_change | portfolio_shift
    "title": "Conversions dropped while traffic held steady",
    "category": "incident",           // incident | seasonality
    "severity": "critical",           // medium | high | critical
    "routing": "immediate",           // immediate | digest
    "first_date": "2026-02-20", "last_date": "2026-02-26",
    "explanation": "Conversions fell to 11, compared with a baseline of 146 (median of the previous 28 days; normal range 62 to 229). That is 92% below baseline (robust z-score -7.4). Clicks stayed within their normal range (3,152 vs baseline 2,922). ... This may indicate a conversion-tracking or tag problem or a genuine drop in landing-page or checkout performance. Suggested first check: Verify the conversion tag is firing ...",
    "possible_causes": ["..."], "diagnostic_steps": ["..."],
    "primary": { "metric": "conversions", "observed": 11.0, "expected": 145.5, "lower": 62.47, "upper": 228.53,
                 "score": -7.35, "pct_change": -0.92, "direction": "down", "severity": "critical",
                 "history_points": 28, "method": "rolling_median_poisson" },
    "occurrences": [{ "date": "2026-02-20", "status": "new", "severity": "critical", "explanation": "...",
                      "primary": { }, "related": [{ }] }],
    "notifications": [{ "date": "2026-02-20", "kind": "new", "routing": "immediate" }],
    "suppressed_count": 6, "reopened_from": null, "suppression_eligible": false
  }],
  "timeline": [{ "campaign_id": "C01", "campaign_name": "...", "points": [
    { "date": "2026-01-31", "values": { "spend": 89844.08 }, "expected": { "spend": 85432.78 },
      "lower": { }, "upper": { }, "anomaly_metrics": [] } ] }],
  "warnings": [],
  "evaluation": { "available": true, "reason": null, "precision": 0.1724, "recall": 1.0, "f1_score": 0.2941,
                  "precision_immediate": 1.0, "alerts_evaluated": 29, "missed_incidents": [],
                  "detected_incidents": [ ], "false_positive_alert_ids": [ ], "non_incident_windows": [ ],
                  "matching_rule": "...", "notes": ["Detector thresholds were chosen while looking at this same dataset ..."],
                  "naive_baseline": { "rule": "...", "alerts_fired": 1103, "precision": 0.0145, "recall": 0.75 } },
  "score_note": "score is a robust z-score ... It is a heuristic score, not a probability."
}
```

- Alerts are sorted with immediate first, then by severity, then by date.
- `timeline` has one entry per campaign, with every day's values and the expected value and band for each metric. It is null where a day can't be scored. For count metrics, the band is a normal approximation of the Poisson rule.
- With no label column, `evaluation.available` is `false`, all metrics are `null`, and `reason` explains why.

## Limitations and assumptions

- **No persistence.** Alert state (cooldowns, open episodes) exists only within one analysis request. Nothing survives a restart, and nothing claims to.
- **No day-of-week model.** Weekend dips widen each campaign's band rather than being modeled.
- **Seasonality detection needs ≥5 campaigns** that can be scored on the same day.
- **Overall precision on the synthetic data is low (17%)** because of medium-severity digest alerts on random outliers. Pages (immediate alerts) were 4 of 4 correct, but that is a tiny sample.
- **Scores are heuristic, not probabilities.** Causes are suggestions to check, never confirmed root causes.
- **The demo data is synthetic and the thresholds were tuned on it.** Expect different numbers on the official dataset.
- **Response size.** The response for 20 campaigns × 180 days is about 3 MB, mostly the timeline.
- **One outage can produce two alerts.** Near the end of a long outage, the alert type can switch (for example from `delivery_drop` to `volume_change`), which opens a second alert. This happened for C12.

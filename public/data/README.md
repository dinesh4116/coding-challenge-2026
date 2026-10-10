# PS-04 — Campaign Anomaly Alerting · Dataset

**File:** `daily_campaign_metrics.csv` — 3,600 rows: 20 campaigns × 180 days (1 Mar – 27 Aug 2026).
One row per campaign per day. All data is synthetic.

| Column | Meaning |
|---|---|
| date | Day (YYYY-MM-DD) |
| campaign_id | C01 – C20 |
| campaign_name | Human-readable name (platform, campaign type) |
| channel | Ad platform: Google Search, Google Shopping, Meta, LinkedIn, TikTok, etc. |
| vertical | `ecommerce` (sells products online) or `b2b` (collects leads for a sales team) |
| landing_page_group | Which website page the ads send people to. Campaigns sharing a group share a page. |
| spend | Money spent that day (USD) |
| impressions | Times ads were shown |
| clicks | Clicks on ads |
| conversions | Purchases (ecommerce) or leads (b2b) |
| revenue | Purchase value (USD). Always 0 for b2b campaigns — they generate leads, not sales. |

**Your job:** flag days and campaigns where something has genuinely gone wrong, explain each alert in
plain English (what changed, by how much, against what normal level), and stay quiet the rest of the time.

**Useful facts:** B2B campaigns are much quieter at weekends by design. Small campaigns swing a lot from
chance. A handful of real incidents are hidden in the data — report how many alerts your system fires in
total, and how many of them you think are real.

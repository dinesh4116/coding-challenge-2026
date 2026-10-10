# Adomaly

Hackathon prototype for **PS-04: Campaign Anomaly Alerting Without Alert Fatigue**.
Adomaly monitors daily advertising campaign metrics, flags anomalies against each
campaign's own history, routes uncertain cases to human review, and groups repeated
alerts into incident episodes.

**Status:** Synthetic benchmark, detection engine (incl. PS-04 dataset support) and Streamlit dashboard built. Evaluation stage pending.

## Synthetic-data limitation
No official dataset was available, so Adomaly uses a **deterministic synthetic
benchmark** (seed 42). Any results reported on it show how the system behaves on
designed scenarios. They are **not** evidence of real-world advertising performance.

## Dataset
15 campaigns × 180 days (2026-01-01 to 2026-06-29), columns
`date, campaign_id, spend, impressions, clicks, conversions`.

- Size tiers: C01–C05 small, C06–C10 medium, C11–C15 large. Small campaigns have
  few conversions per day, so they are naturally noisy.
- Counts come from latent CPM, CTR and CVR rates, so `conversions ≤ clicks ≤ impressions`
  always holds. Each campaign has its own weekend effect, slow trend and noise level.
- 12 labelled incidents: spend spike, conversion-tracking failure, CTR collapse and
  gradual performance degradation. Each type appears in both periods.
- 2 benign events (C06, C10): sustained seasonal budget increases. These are **not**
  incidents, and a good detector should not keep alerting on them.

| File | Purpose | Used by detector? |
|---|---|---|
| `data/raw/campaign_metrics.csv` | Daily metrics | Yes |
| `data/raw/incident_labels.csv` | Ground-truth incidents | No, evaluation only |
| `data/raw/benign_events.csv` | Known non-incident shifts | No, evaluation only |

`src/data_io.load_metrics()` rejects any metrics file containing extra columns, so
labels cannot leak into detector input.

## Chronological split
| Period | Dates | Use |
|---|---|---|
| Warm-up | 2026-01-01 to 2026-01-28 | No incidents, so baselines have clean history |
| Development / calibration | 2026-01-01 to 2026-03-31 (days 0–89) | Tune thresholds and policy |
| Held-out evaluation | 2026-04-01 to 2026-06-29 (days 90–179) | Report results only |

No incident crosses the boundary. Detectors may use metric history up to day *t*
(including dev-period metrics when scoring eval days), but never future days or labels.

## Setup and run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m src.data_generation   # writes data/raw/*.csv
python -m pytest                # runs tests
streamlit run app.py            # dashboard (needs data/raw/daily_campaign_metrics.csv)
```

## Dashboard
`streamlit run app.py` loads the organizer-supplied PS-04 file
`data/raw/daily_campaign_metrics.csv` and runs `src.pipeline.run_ps04_detection` on it
(cached). Tabs: Overview, Campaign explorer, Anomalies, Alert routing, Alert fatigue,
About & limitations; flagged records, routes and episodes export to CSV. Sidebar filters
(channel, vertical, campaign, dates) change the view only; detection always runs on the
full history. The PS-04 data has no ground-truth labels, so flags are signals to
investigate, not confirmed incidents, and evidence strength is a heuristic, not a probability.

## Layout
```
app.py              Streamlit dashboard (PS-04 dataset)
src/config.py       Seed, dates, split, file paths
src/data_generation.py  Synthetic benchmark generator
src/data_io.py      Loaders that keep metrics and labels separate
tests/              pytest suite
data/raw/  data/processed/  outputs/
```

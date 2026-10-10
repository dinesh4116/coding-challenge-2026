"""Central configuration for the Adomaly synthetic benchmark."""
from pathlib import Path

import pandas as pd

SEED = 42
N_CAMPAIGNS = 15
N_DAYS = 180
START_DATE = pd.Timestamp("2026-01-01")
END_DATE = START_DATE + pd.Timedelta(days=N_DAYS - 1)  # 2026-06-29

# Chronological split. Detectors may use any *metric* history up to day t,
# but thresholds/policies are tuned only on DEV and reported only on EVAL.
WARMUP_DAYS = 28  # no incidents here, so every campaign has clean history
DEV_START = START_DATE
DEV_END = START_DATE + pd.Timedelta(days=89)    # 2026-03-31 (days 0-89)
EVAL_START = DEV_END + pd.Timedelta(days=1)     # 2026-04-01
EVAL_END = END_DATE                             # 2026-06-29 (days 90-179)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"

METRICS_FILE = RAW_DIR / "campaign_metrics.csv"      # detector input
LABELS_FILE = RAW_DIR / "incident_labels.csv"        # ground truth, evaluation only
BENIGN_FILE = RAW_DIR / "benign_events.csv"          # non-incident shifts, evaluation only

METRIC_COLUMNS = ["date", "campaign_id", "spend", "impressions", "clicks", "conversions"]
LABEL_COLUMNS = [
    "incident_id", "campaign_id", "incident_type", "start_date", "end_date",
    "affected_metric", "severity", "magnitude", "period",
]
INCIDENT_TYPES = [
    "spend_spike", "tracking_failure", "ctr_collapse", "gradual_degradation",
]

# ---------------------------------------------------------------------------
# PS-04 supplied dataset (real, organizer-provided; kept fully separate from
# the synthetic benchmark above - different file, different column set, no
# ground-truth labels). See README.md "PS-04 supplied dataset" section.
# ---------------------------------------------------------------------------
PS04_FILE = RAW_DIR / "daily_campaign_metrics.csv"   # detector input

# Column order as supplied by the organizers.
PS04_RAW_COLUMNS = [
    "date", "campaign_id", "campaign_name", "channel", "vertical",
    "landing_page_group", "spend", "impressions", "clicks", "conversions", "revenue",
]
# Subset the detector is allowed to score on (metrics only, no metadata).
PS04_METRIC_COLUMNS = [
    "date", "campaign_id", "spend", "impressions", "clicks", "conversions", "revenue",
]
# Per-campaign descriptive fields, kept out of the detector and joined back onto
# records afterwards for grouping/dashboard filters only.
PS04_METADATA_COLUMNS = ["campaign_id", "campaign_name", "channel", "vertical", "landing_page_group"]

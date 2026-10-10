"""Reproducible evaluation report for Adomaly.

Run:  python -m scripts.run_evaluation

Produces, under reports/evaluation/:
  report.md                      - human-readable report with definitions,
                                    assumptions and limitations
  synthetic_metrics.json         - record-level P/R/F1 + fatigue (eval split)
  synthetic_incident_results.csv - per-incident detection + delay
  synthetic_false_alerts.json    - flags on labelled benign shifts
  ps04_metrics.json              - alert-fatigue only (no labels exist)
  alert_fatigue_comparison.csv   - synthetic vs PS-04, side by side

Uses the existing detection pipeline and existing default thresholds
(src/detector_config.py DetectorConfig()) exactly as shipped; this script
does not tune or alter them.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src import config as C
from src.data_io import load_benign, load_labels, load_metrics, load_ps04_metrics
from src.evaluation import (
    alert_fatigue_summary,
    false_alerts_on_benign,
    incident_level_results,
    label_records,
    record_level_metrics,
)
from src.pipeline import run_detection, run_ps04_detection

REPORT_DIR = C.ROOT / "reports" / "evaluation"


def _fmt_pct(x: float) -> str:
    return "n/a" if pd.isna(x) else f"{x * 100:.1f}%"


def _fmt(x) -> str:
    return "n/a" if (isinstance(x, float) and pd.isna(x)) else str(x)


def run_synthetic_evaluation():
    metrics = load_metrics()
    labels = load_labels()
    benign = load_benign()
    records, episodes = run_detection(metrics)

    labelled = label_records(records, labels, benign)
    eval_labelled = labelled[labelled["period"] == "eval"]
    eval_records = records[records["period"] == "eval"]
    eval_episodes = episodes  # episodes aren't period-tagged; see note in report

    rl = record_level_metrics(eval_labelled)
    inc_results = incident_level_results(records, labels)  # all periods, for reference
    inc_results_eval = inc_results[inc_results["period"] == "eval"]
    false_alerts = false_alerts_on_benign(labelled[labelled["period"] == "eval"])
    fatigue = alert_fatigue_summary(records, episodes)
    fatigue_eval = alert_fatigue_summary(eval_records,
                                          episodes[episodes["end_date"] >= C.EVAL_START])

    detection_rate_eval = (inc_results_eval["detected"].mean()
                           if len(inc_results_eval) else float("nan"))
    delays = inc_results_eval.loc[inc_results_eval["detected"], "delay_days"]

    return {
        "record_level": rl,
        "incident_results_all": inc_results,
        "incident_results_eval": inc_results_eval,
        "detection_rate_eval": detection_rate_eval,
        "mean_delay_days_eval": float(delays.mean()) if len(delays) else float("nan"),
        "median_delay_days_eval": float(delays.median()) if len(delays) else float("nan"),
        "false_alerts_eval": false_alerts,
        "fatigue_full": fatigue,
        "fatigue_eval": fatigue_eval,
        "n_dev_incidents": int((labels["period"] == "dev").sum()),
        "n_eval_incidents": int((labels["period"] == "eval").sum()),
    }


def run_ps04_evaluation():
    metrics, metadata = load_ps04_metrics()
    records, episodes = run_ps04_detection(metrics, metadata)
    fatigue = alert_fatigue_summary(records, episodes)
    return {"fatigue": fatigue, "n_campaigns": int(metrics["campaign_id"].nunique()),
            "n_records": int(len(records))}


def write_outputs(syn: dict, ps04: dict):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rl = syn["record_level"]

    # ---- JSON ----
    (REPORT_DIR / "synthetic_metrics.json").write_text(json.dumps({
        "evaluation_unit": "(campaign_id, metric, date), metric in "
                           "{spend, conversions, ctr}, EVAL split only",
        "record_level": vars(rl),
        "incident_level": {
            "n_eval_incidents": syn["n_eval_incidents"],
            "detection_rate_eval": syn["detection_rate_eval"],
            "mean_delay_days_eval": syn["mean_delay_days_eval"],
            "median_delay_days_eval": syn["median_delay_days_eval"],
        },
        "false_alerts_on_labelled_benign_shifts_eval": syn["false_alerts_eval"],
        "alert_fatigue_eval_split": syn["fatigue_eval"],
        "alert_fatigue_full_dataset": syn["fatigue_full"],
    }, indent=2, default=str))

    syn["incident_results_all"].to_csv(REPORT_DIR / "synthetic_incident_results.csv", index=False)
    (REPORT_DIR / "synthetic_false_alerts.json").write_text(
        json.dumps(syn["false_alerts_eval"], indent=2, default=str))

    (REPORT_DIR / "ps04_metrics.json").write_text(json.dumps({
        "note": "PS-04 has no ground-truth labels. Precision, recall, F1 and "
                "incident-level detection rate are NOT computed and MUST NOT be "
                "inferred from this file. Only alert-fatigue volume is measured.",
        **ps04,
    }, indent=2, default=str))

    comp = pd.DataFrame([
        {"dataset": "Synthetic (eval split)", **syn["fatigue_eval"]},
        {"dataset": "Synthetic (full)", **syn["fatigue_full"]},
        {"dataset": "PS-04 (official, no labels)", **ps04["fatigue"]},
    ])
    comp.to_csv(REPORT_DIR / "alert_fatigue_comparison.csv", index=False)

    # ---- Markdown ----
    inc_eval = syn["incident_results_eval"]
    lines = []
    lines.append("# Adomaly — Evaluation Report\n")
    lines.append("Generated by `scripts/run_evaluation.py` against the existing detection "
                 "pipeline (`src/pipeline.py`) with its shipped default thresholds "
                 "(`src/detector_config.py: DetectorConfig()`), unmodified.\n")

    lines.append("\n## 1. Matching rule and evaluation unit\n")
    lines.append(
        "- Evaluation unit: `(campaign_id, metric, date)`.\n"
        "- An incident's `affected_metric` is mapped to a detector metric: "
        "`spend->spend`, `conversions->conversions`, `ctr->ctr`, "
        "`conversion_rate->conversions` (the same mapping already used by "
        "`tests/test_detection.py::test_dev_benchmark_incidents_are_flagged`).\n"
        "- A record is **flagged** if its route is `Alert` or `Human Review` "
        "(both reach a human; `No Alert` does not).\n"
        "- A record **detects** an incident if it is flagged, its metric matches the "
        "incident's mapped metric, its campaign matches, and its date falls inside "
        "`[start_date, end_date]`.\n")

    lines.append("\n## 2. Synthetic benchmark — record-level precision / recall / F1\n")
    lines.append(
        "**Split:** EVAL only (chronologically after `DEV_END`). Thresholds in "
        "`DetectorConfig()` were chosen on the DEV period only "
        "(see comment in `src/detector_config.py`), so reporting on DEV would score "
        "the detector on its own tuning set. All numbers below are EVAL-only.\n\n"
        "**Why P/R/F1 are valid here:** the synthetic generator's incident and "
        "benign-event lists are exhaustive — every injected anomalous or shifted "
        "period is labelled — so a `(campaign, metric, date)` outside a labelled "
        "incident window is a genuine negative, not an unlabeled unknown. The "
        "universe is restricted to `metric in {spend, conversions, ctr}` because no "
        "label targets `impressions`, `clicks`, `cvr` or `revenue`; flags on those "
        "are reported separately as informational only, never as false positives.\n\n")
    lines.append(f"- Evaluated records: **{rl.n_evaluated}** "
                 f"(positive: {rl.n_positive}, negative: {rl.n_negative})\n"
                 f"- TP={rl.tp}  FP={rl.fp}  FN={rl.fn}  TN={rl.tn}\n"
                 f"- **Precision: {_fmt_pct(rl.precision)}**\n"
                 f"- **Recall: {_fmt_pct(rl.recall)}**\n"
                 f"- **F1: {_fmt(round(rl.f1, 3) if pd.notna(rl.f1) else rl.f1)}**\n"
                 f"- Flags on unmapped metrics (informational, not scored): "
                 f"{rl.n_unmapped_metric_flags}\n")

    lines.append("\n## 3. Incident-level detection rate and delay (EVAL split)\n")
    lines.append(f"- Incidents in EVAL split: **{syn['n_eval_incidents']}**\n"
                 f"- **Detection rate: {_fmt_pct(syn['detection_rate_eval'])}** "
                 f"({int(inc_eval['detected'].sum())}/{len(inc_eval)} incidents had at least "
                 "one flagged record on the mapped metric inside their window)\n"
                 f"- Mean detection delay (detected incidents only): "
                 f"{_fmt(round(syn['mean_delay_days_eval'], 1) if pd.notna(syn['mean_delay_days_eval']) else syn['mean_delay_days_eval'])} days\n"
                 f"- Median detection delay: "
                 f"{_fmt(syn['median_delay_days_eval'])} days\n\n"
                 "Per-incident detail:\n\n")
    lines.append("| incident_id | campaign | type | metric | severity | detected | delay (days) |\n"
                 "|---|---|---|---|---|---|---|\n")
    for r in inc_eval.itertuples():
        lines.append(f"| {r.incident_id} | {r.campaign_id} | {r.incident_type} | "
                     f"{r.mapped_metric} | {r.severity} | {'yes' if r.detected else '**no**'} | "
                     f"{_fmt(round(r.delay_days,0) if pd.notna(r.delay_days) else r.delay_days)} |\n")

    fa = syn["false_alerts_eval"]
    lines.append("\n## 4. False alerts on labelled benign (non-incident) shifts — EVAL split\n\n")
    lines.append(
        "Benign events are deliberate, sustained shifts (e.g. a planned budget increase) "
        "that a good detector should stop re-flagging once past the baseline window.\n\n"
        f"- Benign-shift records in EVAL: {fa['benign_shift_records']}\n"
        f"- Flagged (Alert/Review): {fa['benign_shift_flagged_records']} "
        f"({_fmt_pct(fa['benign_shift_flag_rate'])})\n"
        f"- Of those, routed to Alert: {fa['benign_shift_alert_records']}\n")

    lines.append("\n## 5. Alert-fatigue behaviour\n")
    for label, d in [("Synthetic, EVAL split", syn["fatigue_eval"]),
                     ("Synthetic, full dataset", syn["fatigue_full"]),
                     ("PS-04 (official, no labels)", ps04["fatigue"])]:
        lines.append(f"\n**{label}**\n\n"
                     f"- Raw flagged records (naive per-day alerting): {d['raw_flagged_records']}\n"
                     f"- Alerts: {d['alerts']}  ·  Human Review: {d['human_review_records']}\n"
                     f"- Episodes: {d['episodes']}\n"
                     f"- Notifications actually sent: {d['notifications_sent']} "
                     f"(new: {d['new_episode_notifications']}, escalation: {d['escalation_notifications']})\n"
                     f"- Suppressed repeats: {d['suppressed_repeats']}\n"
                     f"- Notification reduction vs raw flags: {_fmt_pct(d['notification_reduction_pct']/100 if pd.notna(d['notification_reduction_pct']) else d['notification_reduction_pct'])}\n")

    lines.append("\n## 6. PS-04 official dataset\n")
    lines.append(
        f"- Campaigns: {ps04['n_campaigns']}  ·  Scored records: {ps04['n_records']}\n"
        "- **No ground-truth labels exist for this dataset.** Precision, recall, F1 and "
        "incident-level detection rate are not computed and must not be inferred from "
        "this report. Only the alert-fatigue volume numbers above (section 5) apply to it.\n")

    lines.append("\n## 7. Assumptions and limitations\n")
    lines.append(
        "- Detector thresholds are the shipped defaults; this evaluation does not tune them.\n"
        "- Metrics are computed only over `metric in {spend, conversions, ctr}`; "
        "`impressions`, `clicks`, `cvr` and `revenue` flags are not scored against any label.\n"
        "- `conversion_rate` incidents (gradual_degradation) are matched on the `conversions` "
        "metric, not `cvr`, for consistency with the project's own existing test "
        "(`test_dev_benchmark_incidents_are_flagged`); a `cvr` flag on the same incident is "
        "not separately credited or penalized.\n"
        "- Episode objects aren't period-tagged in `src/episodes.py`; the EVAL-split fatigue "
        "numbers approximate this by filtering episodes whose `end_date` falls in or after "
        "the EVAL period, and by scoring fatigue over EVAL-period records directly for the "
        "primary record-count figures.\n"
        "- Detection delay is measured in calendar days from an incident's documented "
        "`start_date`, not from when the detector had enough history — an incident that "
        "starts before a campaign has `min_history` days of data could show as 'not detected' "
        "for a reason unrelated to detector sensitivity. None of the EVAL incidents are this "
        "early in their campaign's history, but this is a theoretical gap in the method.\n"
        "- The synthetic benchmark is a designed scenario set, not a sample of real campaign "
        "incidents; these numbers describe behaviour on that benchmark, not real-world "
        "performance, exactly as `app.py`'s own About tab already states.\n")

    (REPORT_DIR / "report.md").write_text("".join(lines))


if __name__ == "__main__":
    syn = run_synthetic_evaluation()
    ps04 = run_ps04_evaluation()
    write_outputs(syn, ps04)
    rl = syn["record_level"]
    print(f"EVAL split: precision={rl.precision:.3f} recall={rl.recall:.3f} "
          f"f1={rl.f1:.3f} (TP={rl.tp} FP={rl.fp} FN={rl.fn})")
    print(f"Incident detection rate (eval): {syn['detection_rate_eval']:.1%} "
          f"({int(syn['incident_results_eval']['detected'].sum())}/{syn['n_eval_incidents']})")
    print(f"Wrote reports to {REPORT_DIR.relative_to(C.ROOT)}/")

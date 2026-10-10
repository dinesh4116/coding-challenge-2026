"""Command-line report: the problem statement's minimum bar in one command.

    python -m app.cli data/demo_campaigns.csv [--cooldown-days 3] [--json out.json]

Prints how many alerts were fired in total, how they were routed, precision/
recall against labels (if present), the incidents missed, and how many alerts
the naive ±30% rule would have fired on the same data.
"""
import argparse
import sys
from pathlib import Path

from app.config import get_settings
from app.services.alert_manager import AlertConfig
from app.services.data_loader import DataValidationError
from app.services.detector import DetectorConfig
from app.services.pipeline import AnalysisConfig, analyze_csv


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    p = argparse.ArgumentParser(description="Campaign anomaly alerting report")
    p.add_argument("csv", type=Path)
    p.add_argument("--window-days", type=int, default=28)
    p.add_argument("--min-history", type=int, default=14)
    p.add_argument("--z-threshold", type=float, default=3.5)
    p.add_argument("--cooldown-days", type=int, default=3)
    p.add_argument("--json", type=Path, help="also write the full API response to this file")
    args = p.parse_args(argv)

    config = AnalysisConfig(
        detector=DetectorConfig(window_days=args.window_days, min_history=args.min_history,
                                z_threshold=args.z_threshold),
        alerts=AlertConfig(cooldown_days=args.cooldown_days))
    try:
        result = analyze_csv(args.csv.read_bytes(), config, get_settings().max_rows)
    except DataValidationError as exc:
        print(f"Cannot analyze {args.csv}: {exc}")
        return 2

    s, ev = result.summary, result.evaluation
    print(f"Analyzed {s.campaigns_analyzed} campaigns, {s.records_analyzed} records, "
          f"{s.date_start} to {s.date_end}")
    print(f"Total alerts fired over {s.days_covered} days: {s.notifications_sent} "
          f"({s.immediate_notifications} immediate, {s.digest_notifications} digest)")
    print(f"Anomalies detected: {s.anomalies_detected} / grouped: {s.grouped_alerts} / "
          f"suppressed: {s.suppressed_alerts} / escalated: {s.escalated_alerts} / reopened: {s.reopened_alerts}")
    seasonal = sum(a.category == "seasonality" for a in result.alerts)
    print(f"Alert episodes: {s.alerts_total} ({seasonal} routed as seasonality)")
    if ev.available:
        print(f"Precision / Recall / F1: {_pct(ev.precision)} / {_pct(ev.recall)} / {_pct(ev.f1_score)} "
              f"({ev.true_positive_alerts} of {ev.alerts_evaluated} incident alerts matched; "
              f"{ev.incidents_detected} of {ev.incidents_total} incidents caught)")
        print(f"Precision of immediate alerts: {_pct(ev.precision_immediate)} "
              f"({ev.immediate_alerts_evaluated} immediate incident alerts)")
        for d in ev.detected_incidents:
            print(f"  caught: {d['campaign_id']} {d['incident_type']} {d['start']}..{d['end']} "
                  f"(first alert {d['first_alert_date']}, +{d['days_to_detect']} days)")
        for m in ev.missed_incidents:
            print(f"  MISSED: {m['campaign_id']} {m['incident_type']} {m['start']}..{m['end']}")
    else:
        print(f"Precision / Recall / F1: n/a — {ev.reason}")
    nb = ev.naive_baseline or {}
    print(f"Naive ±30% day-over-day rule would have fired: {nb.get('alerts_fired')} alerts "
          f"(precision {_pct(nb.get('precision'))}, recall {_pct(nb.get('recall'))})")
    for w in result.warnings[:10]:
        print(f"warning: {w}")
    if args.json:
        args.json.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"Full response written to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Turn a campaign-day's anomalies into an alert type and a plain-English explanation.

A small, ordered rule table (first match wins) recognises common patterns,
e.g. "conversions fell but clicks are normal" -> possible tracking issue.
Every sentence is built from measured values, and causes are always
phrased as possibilities with a first check to run, never as confirmed.
"""
from dataclasses import dataclass
from typing import Callable

from app.services.detector import Anomaly

NORMAL_SCORE = 2.5  # |score| below this counts as "within normal range" for context

METRIC_LABELS = {
    "impressions": "Impressions", "clicks": "Clicks", "spend": "Spend",
    "conversions": "Conversions", "revenue": "Revenue", "ctr": "Click-through rate",
    "cvr": "Conversion rate", "cpc": "Cost per click", "cpa": "Cost per acquisition",
    "roas": "Return on ad spend",
}
COUNT_LIKE = {"impressions", "clicks", "conversions"}
MONEY_LIKE = {"spend", "revenue", "cpc", "cpa"}
PERCENT_LIKE = {"ctr", "cvr"}


@dataclass
class Diagnosis:
    alert_type: str
    title: str
    explanation: str
    possible_causes: list[str]
    diagnostic_steps: list[str]


def format_value(metric: str, value: float) -> str:
    if metric in COUNT_LIKE:
        return f"{round(value):,}"
    if metric in PERCENT_LIKE:
        return f"{value * 100:.2f}%"
    if metric == "roas":
        return f"{value:.2f}x"
    return f"{value:,.2f}"  # money: currency unknown, so no symbol


def describe_anomaly(a: Anomaly) -> str:
    label = METRIC_LABELS.get(a.metric, a.metric)
    verb = "rose" if a.direction == "up" else "fell"
    side = "above" if a.direction == "up" else "below"
    return (f"{label} {verb} to {format_value(a.metric, a.observed)}, compared with a baseline of "
            f"{format_value(a.metric, a.expected)} (median of the previous {a.history_points} days; "
            f"normal range {format_value(a.metric, a.lower)} to {format_value(a.metric, a.upper)}). "
            f"That is {abs(a.pct_change) * 100:.0f}% {side} baseline (robust z-score {a.score:+.1f}).")


# ---- the rule table -------------------------------------------------------

@dataclass
class _Context:
    anomalies: dict[str, Anomaly]
    day_scores: dict[str, dict]

    def moved(self, metric: str, direction: str) -> bool:
        a = self.anomalies.get(metric)
        return a is not None and a.direction == direction

    def normal(self, metric: str) -> bool:
        s = self.day_scores.get(metric)
        return (s is not None and s.get("score") is not None and metric not in self.anomalies
                and abs(s["score"]) < NORMAL_SCORE)


@dataclass
class Rule:
    alert_type: str
    title: str
    matches: Callable[[_Context], bool]
    possible_causes: list[str]
    diagnostic_steps: list[str]


RULES: list[Rule] = [
    Rule("tracking_issue", "Conversions dropped while traffic held steady",
         lambda c: (c.moved("conversions", "down") or c.moved("cvr", "down")) and c.normal("clicks"),
         ["a conversion-tracking or tag problem", "a genuine drop in landing-page or checkout performance"],
         ["Verify the conversion tag is firing (tag manager / test conversion) and check for recent site or checkout deploys.",
          "Check that the landing page and checkout load and work correctly.",
          "Compare with conversions recorded in your backend or analytics tool for the same day."]),
    Rule("delivery_drop", "Delivery dropped sharply",
         lambda c: c.moved("spend", "down") and (c.moved("impressions", "down") or c.moved("clicks", "down")),
         ["an exhausted daily or monthly budget", "a paused or disapproved campaign", "a billing or payment problem"],
         ["Check campaign status, daily/monthly budget caps and billing; confirm the budget was not exhausted.",
          "Look for disapproved ads or policy notices.",
          "Check whether the data for this day is complete."]),
    Rule("cost_efficiency_shift", "Cost efficiency changed",
         lambda c: c.moved("cpc", "up") or c.moved("cpa", "up") or c.moved("roas", "down"),
         ["a bid strategy or target change", "increased auction competition", "a change in targeting or audience quality"],
         ["Review the change history for bid strategy, target CPA/ROAS or bid changes around this date.",
          "Compare auction insights / competitor activity for the period.",
          "Check whether targeting or creatives changed recently."]),
    Rule("spend_spike", "Spend spiked",
         lambda c: c.moved("spend", "up"),
         ["a budget increase or bid change", "a targeting or broad-match expansion", "unusual auction pressure"],
         ["Check for budget increases, bid changes or broad-match/targeting expansion; consider a temporary cap.",
          "Confirm the extra spend produced proportional clicks and conversions."]),
    Rule("volume_change", "Unusual change in campaign volume",
         lambda c: True,
         ["a change in traffic or demand", "incomplete or delayed data for this day"],
         ["Check whether traffic volume or data completeness changed for this campaign on this date.",
          "Review recent campaign edits in the change history."]),
]


def _pct(a: Anomaly) -> str:
    return f"{a.pct_change * 100:+.0f}%"


def diagnose(anomalies: list[Anomaly], day_scores: dict[str, dict]) -> Diagnosis:
    """`anomalies` is sorted with the primary anomaly first."""
    ctx = _Context({a.metric: a for a in anomalies}, day_scores)
    rule = next(r for r in RULES if r.matches(ctx))
    primary = anomalies[0]

    sentences = [describe_anomaly(primary)]
    if rule.alert_type == "tracking_issue":
        clicks = day_scores["clicks"]
        sentences.append(f"Clicks stayed within their normal range ({format_value('clicks', clicks['observed'])} "
                         f"vs baseline {format_value('clicks', clicks['expected'])}).")
    related = anomalies[1:]
    if related:
        sentences.append("Related changes: " + ", ".join(
            f"{METRIC_LABELS.get(a.metric, a.metric)} {_pct(a)}" for a in related) + ".")
    causes = rule.possible_causes
    sentences.append(f"This may indicate {', '.join(causes[:-1])} or {causes[-1]}." if len(causes) > 1
                     else f"This may indicate {causes[0]}.")
    sentences.append(f"Suggested first check: {rule.diagnostic_steps[0]}")
    return Diagnosis(alert_type=rule.alert_type, title=rule.title, explanation=" ".join(sentences),
                     possible_causes=list(causes), diagnostic_steps=list(rule.diagnostic_steps))

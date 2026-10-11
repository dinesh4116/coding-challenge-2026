"""CSV ingestion: raw upload bytes -> clean, canonical daily frame + warnings.

Each validation rule is one small helper so it can be pointed at in a demo.
Bad values are never silently "fixed": invalid dates are dropped, bad or
negative numbers become missing, and every such action produces a warning.
Warnings contain counts and column names only, never row values.
"""
import csv
import io
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

CANONICAL_METRICS = ("impressions", "clicks", "spend", "conversions", "revenue")

# normalized header -> canonical column name
COLUMN_ALIASES: dict[str, str] = {
    "campaign_id": "campaign_id", "campaign": "campaign_id", "campaignid": "campaign_id",
    "campaign_name": "campaign_name",
    "date": "date", "day": "date", "report_date": "date", "ds": "date", "timestamp": "date",
    "impressions": "impressions", "impr": "impressions", "imps": "impressions",
    "clicks": "clicks",
    "spend": "spend", "cost": "spend", "amount_spent": "spend", "ad_spend": "spend",
    "conversions": "conversions", "conv": "conversions", "convs": "conversions",
    "purchases": "conversions", "results": "conversions",
    "revenue": "revenue", "conversion_value": "revenue", "conv_value": "revenue",
    "purchase_value": "revenue", "sales": "revenue",
    "is_incident": "is_incident", "is_anomaly": "is_incident", "anomaly": "is_incident",
    "label": "is_incident", "incident": "is_incident",
    "critical_warning": "is_incident",
    "incident_type": "incident_type", "anomaly_type": "incident_type",
    "ground_truth_label": "incident_type",
    "alert_severity": "alert_severity",
    "incident_id": "incident_id",
}
TRUE_LABELS = {"1", "1.0", "true", "yes", "y", "t", "critical"}


class DataValidationError(ValueError):
    """Raised when the file cannot be analyzed. The message is shown to the user."""


@dataclass
class LoadResult:
    frame: pd.DataFrame
    metrics: list[str]
    has_labels: bool
    warnings: list[str] = field(default_factory=list)
    input_rows: int = 0
    valid_rows: int = 0


def load_csv_bytes(content: bytes, max_rows: int) -> LoadResult:
    raw = _read_csv(content)
    if len(raw) > max_rows:
        raise DataValidationError(f"File has {len(raw)} rows; the limit is {max_rows}.")
    return normalize_frame(raw)


def normalize_frame(raw: pd.DataFrame) -> LoadResult:
    warnings: list[str] = []
    input_rows = len(raw)
    df = _apply_aliases(_normalize_headers(raw), warnings)
    metrics = [m for m in CANONICAL_METRICS if m in df.columns]
    _check_required(df, metrics)

    df = _parse_dates(df, warnings)
    # ';'-delimited files come from locales that write 12,5 for twelve and a half
    decimal_comma = raw.attrs.get("delimiter") == ";" and any(
        df[m].astype("string").str.contains(",", regex=False).any() for m in metrics)
    if decimal_comma:
        warnings.append("Detected decimal comma number format (e.g. 1.234,50); ',' read as the decimal point.")
    for m in metrics:
        df[m] = _parse_numeric(df[m], m, warnings, decimal_comma)
    if "is_incident" in df.columns:
        has_labels = True
        df["is_incident"] = df["is_incident"].astype(str).str.strip().str.lower().isin(TRUE_LABELS).astype(int)
    elif "incident_type" in df.columns:
        non_incident_labels = {"normal", "none", "", "nan", "0", "false"}
        df["is_incident"] = (~df["incident_type"].astype(str).str.strip().str.lower().isin(non_incident_labels)).astype(int)
        has_labels = bool(df["is_incident"].any())
    else:
        has_labels = False

    if "incident_type" in df.columns:
        df["incident_type"] = df["incident_type"].fillna("").astype(str).str.strip()

    df = _handle_duplicates(df, metrics, warnings)
    if df.empty:
        raise DataValidationError("The file contains no valid records after validation.")
    valid_rows = len(df)
    df = _fill_missing_days(df, metrics, warnings)
    return LoadResult(frame=df, metrics=metrics, has_labels=has_labels, warnings=warnings,
                      input_rows=input_rows, valid_rows=valid_rows)


def _read_csv(content: bytes) -> pd.DataFrame:
    """Read every column as text; we parse types ourselves so nothing is guessed silently."""
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if not text.strip():
        raise DataValidationError("Could not parse CSV: the file is empty.")
    first_line = text.lstrip().splitlines()[0]
    delimiter = max([",", ";", "\t"], key=first_line.count)  # Excel in some locales uses ';'
    try:
        raw = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str, quoting=csv.QUOTE_MINIMAL)
        raw.attrs["delimiter"] = delimiter
        return raw
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise DataValidationError(f"Could not parse CSV: {exc}") from exc


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    def norm(name: str) -> str:
        name = str(name).replace("﻿", "").strip().lower()
        return re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return df.rename(columns={c: norm(c) for c in df.columns})


def _apply_aliases(df: pd.DataFrame, warnings: list[str]) -> pd.DataFrame:
    renamed: dict[str, str] = {}
    has_id_column = any(c in ("campaign_id", "campaignid") for c in df.columns)
    for col in df.columns:
        target = COLUMN_ALIASES.get(col)
        if col == "campaign" and has_id_column:
            target = "campaign_name"  # e.g. Google Ads: "Campaign" is the name, "Campaign ID" the ID
        if target is None:
            continue
        if target in renamed.values():
            warnings.append(f"Column '{col}' ignored: another column already maps to '{target}'.")
            continue
        renamed[col] = target
    out = df[list(renamed)].rename(columns=renamed)
    if "campaign_id" not in out.columns and "campaign_name" in out.columns:
        out["campaign_id"] = out["campaign_name"]  # name doubles as the ID when no ID column exists
    return out


def _check_required(df: pd.DataFrame, metrics: list[str]) -> None:
    missing = [c for c in ("campaign_id", "date") if c not in df.columns]
    if missing:
        raise DataValidationError(f"Missing required column(s): {', '.join(missing)}.")
    if not metrics:
        raise DataValidationError(
            f"No metric columns found. Expected at least one of: {', '.join(CANONICAL_METRICS)}.")


def _parse_dates(df: pd.DataFrame, warnings: list[str]) -> pd.DataFrame:
    df = df.copy()
    df["campaign_id"] = df["campaign_id"].astype("string").str.strip()
    df["date"] = _to_dates(df["date"], warnings)
    bad = df["date"].isna() | df["campaign_id"].isna() | (df["campaign_id"] == "")
    if bad.any():
        warnings.append(f"{int(bad.sum())} row(s) dropped: invalid or missing date/campaign_id.")
    df = df[~bad].copy()
    df["campaign_id"] = df["campaign_id"].astype(str)
    return df


def _to_dates(raw: pd.Series, warnings: list[str]) -> pd.Series:
    """ISO dates first; otherwise try month-first and day-first and keep the one that makes sense.

    Timezone offsets are dropped, keeping each row's own local calendar date
    (a daily report for "2026-01-02 +05:00" belongs to 2 January).
    """
    def local_date(value, **kw):
        if pd.isna(value) or value is None:
            return pd.NaT
        try:
            ts = pd.to_datetime(value, errors="coerce", **kw)
            if pd.isna(ts):
                return pd.NaT
            if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                return ts.tz_localize(None)
            return ts
        except Exception:
            return pd.NaT

    def parse(**kw) -> pd.Series:
        try:
            d = pd.to_datetime(raw, errors="coerce", **kw)
        except (ValueError, TypeError):  # mixed timezone offsets or types in one column: parse value by value
            d = pd.to_datetime(raw.map(lambda v: local_date(v, **kw)), errors="coerce")
        if hasattr(d, "dt"):
            if getattr(d.dt, "tz", None) is not None:
                d = d.dt.tz_localize(None)
            return d.dt.normalize()
        return pd.to_datetime(raw.map(lambda v: local_date(v, **kw)), errors="coerce").dt.normalize()

    dates = parse(format="ISO8601")
    if dates.isna().mean() <= 0.5:
        return dates
    month_first, day_first = parse(format="mixed"), parse(format="mixed", dayfirst=True)

    def badness(d: pd.Series) -> tuple[int, float]:  # fewer failures first, then the tighter date span
        valid = d.dropna()
        return int(d.isna().sum()), (valid.max() - valid.min()).days if len(valid) else float("inf")

    if badness(day_first) < badness(month_first):
        warnings.append("Dates read as day-first (DD/MM/YYYY).")
        return day_first
    return month_first


def _parse_numeric(values: pd.Series, name: str, warnings: list[str], decimal_comma: bool = False) -> pd.Series:
    cleaned = values.astype("string").str.replace(r"[\s$€£₹]", "", regex=True)
    if decimal_comma:
        cleaned = cleaned.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        cleaned = cleaned.str.replace(",", "", regex=False)
    cleaned = cleaned.replace("", pd.NA)
    numbers = pd.to_numeric(cleaned, errors="coerce").astype(float)
    numbers = numbers.where(np.isfinite(numbers))  # "inf" is not a usable metric value
    non_numeric = int((cleaned.notna() & numbers.isna()).sum())
    if non_numeric:
        warnings.append(f"{name}: {non_numeric} non-numeric value(s) treated as missing.")
    negative = numbers < 0
    if negative.any():
        warnings.append(f"{name}: {int(negative.sum())} negative value(s) treated as missing.")
        numbers = numbers.mask(negative)
    return numbers


def _handle_duplicates(df: pd.DataFrame, metrics: list[str], warnings: list[str]) -> pd.DataFrame:
    """Exact duplicates are dropped; remaining same campaign+date rows are summed."""
    before = len(df)
    df = df.drop_duplicates()
    if len(df) < before:
        warnings.append(f"{before - len(df)} exact duplicate row(s) removed.")
    dup_keys = df.duplicated(["campaign_id", "date"], keep=False)
    if dup_keys.any():
        n_keys = int(df.loc[dup_keys, ["campaign_id", "date"]].drop_duplicates().shape[0])
        warnings.append(f"{n_keys} campaign/date pair(s) had multiple rows; "
                        "treated as sub-campaign breakdown rows and summed.")
    if not dup_keys.any():
        return df.sort_values(["campaign_id", "date"]).reset_index(drop=True)
    agg: dict[str, object] = {m: (lambda s: s.sum(min_count=1)) for m in metrics}
    if "is_incident" in df.columns:
        agg["is_incident"] = "max"
    for text_col in ("campaign_name", "incident_type"):
        if text_col in df.columns:
            agg[text_col] = lambda s: next((v for v in s if isinstance(v, str) and v), "")
    return df.groupby(["campaign_id", "date"], as_index=False, sort=True).agg(agg)


def _fill_missing_days(df: pd.DataFrame, metrics: list[str], warnings: list[str]) -> pd.DataFrame:
    parts = []
    for cid, g in df.groupby("campaign_id", sort=True):
        full = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
        g = g.set_index("date").reindex(full)
        g.index.name = "date"
        g["row_present"] = g["campaign_id"].notna()
        missing = int((~g["row_present"]).sum())
        if missing:
            warnings.append(f"{cid}: {missing} missing day(s) filled as gaps (not scored).")
        g["campaign_id"] = cid
        if "campaign_name" in g.columns:
            g["campaign_name"] = g["campaign_name"].ffill().bfill().fillna("")
        if "is_incident" in g.columns:
            g["is_incident"] = g["is_incident"].fillna(0).astype(int)
        if "incident_type" in g.columns:
            g["incident_type"] = g["incident_type"].fillna("")
        parts.append(g.reset_index())
    out = pd.concat(parts, ignore_index=True)
    for text_col in ("campaign_id", "campaign_name", "incident_type"):
        if text_col in out.columns:  # plain Python strings: much faster to iterate than Arrow strings
            out[text_col] = out[text_col].astype(object)
    cols = ["campaign_id", "date", *metrics, "row_present"]
    cols += [c for c in ("campaign_name", "is_incident", "incident_type") if c in out.columns]
    return out[cols]

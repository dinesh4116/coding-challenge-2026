"""
Robust CSV ingestion for SearchPilot AI.

Handles the many shapes a "search terms" CSV can take in the real world:
  * Google Ads UI exports with title / date-range lines above the header
  * UTF-8, UTF-8 with BOM, UTF-16 (Google Ads "Excel .csv"), Windows-1252
  * Comma, tab, semicolon or pipe delimiters
  * Numbers written as "$1,234.56", "12.5%", "1 234,56", "--", "< 10"
  * "Total: ..." summary rows at the bottom of exports
  * Different / missing column names (best-effort mapping with warnings)
"""
import csv
import io
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB safety limit

# standard column -> accepted header names (already normalised: lower-case, single spaces)
COLUMN_ALIASES: Dict[str, List[str]] = {
    "query": [
        "search term", "search terms", "search term (query)", "query", "queries",
        "search query", "search queries", "customer search term", "keyword / search term",
        "search keyword", "user query", "term", "terms", "keyword", "keywords",
    ],
    "campaign": ["campaign", "campaign name", "campaigns"],
    "ad_group": ["ad group", "adgroup", "ad group name", "ad groups", "ad_group"],
    "match_type": [
        "match type", "match_type", "search term match type", "keyword match type",
        "matchtype",
    ],
    "impressions": ["impressions", "impr.", "impr", "impression", "imps"],
    "clicks": ["clicks", "click"],
    "cost": ["cost", "spend", "amount spent", "total cost", "cost (usd)", "cost ($)"],
    "conversions": [
        "conversions", "conv.", "conv", "all conv.", "all conversions", "total conversions",
        "conversion", "orders", "leads",
    ],
    "conversion_value": [
        "conversion value", "conv. value", "total conv. value", "all conv. value",
        "all conversion value", "conversion revenue", "revenue", "value", "sales",
    ],
}

NUMERIC_COLS = ["impressions", "clicks", "cost", "conversions", "conversion_value"]
HEADER_SCAN_LINES = 60


class CsvLoadError(ValueError):
    """Raised with a user-friendly message when a file cannot be used."""


# ----------------------------------------------------------------------------
# Decoding / structure detection
# ----------------------------------------------------------------------------
def _decode(raw: bytes) -> Tuple[str, str]:
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16"), "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    # UTF-16 without BOM: lots of NUL bytes
    if raw[:200].count(b"\x00") > 20:
        for enc in ("utf-16-le", "utf-16-be"):
            try:
                return raw.decode(enc), enc
            except UnicodeDecodeError:
                continue
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("cp1252"), "cp1252"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def _norm(name: object) -> str:
    s = str(name).replace("\ufeff", "").replace("\xa0", " ")
    s = s.strip().strip('"').strip("'").strip()
    return re.sub(r"\s+", " ", s).lower()


def _split_line(line: str, delim: str) -> List[str]:
    try:
        return next(csv.reader([line], delimiter=delim))
    except Exception:
        return line.split(delim)


def _all_aliases() -> set:
    out = set()
    for v in COLUMN_ALIASES.values():
        out.update(v)
    return out


def _detect_header(lines: List[str]) -> Tuple[int, str]:
    """Return (header_line_index, delimiter)."""
    aliases = _all_aliases()
    best = None  # (score, idx, delim)
    candidates = [",", "\t", ";", "|"]

    for idx, line in enumerate(lines[:HEADER_SCAN_LINES]):
        if not line.strip():
            continue
        for delim in candidates:
            if delim not in line:
                continue
            cells = [_norm(c) for c in _split_line(line, delim)]
            if len(cells) < 2:
                continue
            hits = sum(1 for c in cells if c in aliases)
            has_query = any(c in COLUMN_ALIASES["query"] for c in cells)
            score = hits * 10 + (25 if has_query else 0)
            if hits >= 2 or has_query:
                if best is None or score > best[0]:
                    best = (score, idx, delim)
        if best and best[0] >= 45:  # confident enough - stop at first strong header
            break

    if best:
        return best[1], best[2]

    # No recognisable header: use first non-empty line, most common delimiter
    for idx, line in enumerate(lines):
        if line.strip():
            counts = {d: line.count(d) for d in candidates}
            delim = max(counts, key=counts.get)
            if counts[delim] == 0:
                delim = ","
            return idx, delim
    raise CsvLoadError("The file is empty.")


# ----------------------------------------------------------------------------
# Number cleaning
# ----------------------------------------------------------------------------
_NUM_JUNK = re.compile(r"[^\d.,\-+eE]")


def _to_number(series: pd.Series, decimal_comma: bool = False) -> pd.Series:
    s = series.astype(str).str.strip()
    # Google Ads placeholders ("--", "< 10", "> 90%", "n/a") -> 0
    s = s.str.replace(r"^\s*(--+|-|n/?a|null|none|nan|<\s*[\d.,]+%?|>\s*[\d.,]+%?)\s*$", "0", case=False, regex=True)
    neg = s.str.match(r"^\(.*\)$")  # (12.50) accounting negatives
    s = s.str.replace("\xa0", "", regex=False).str.replace(" ", "", regex=False)
    s = s.str.replace(_NUM_JUNK, "", regex=True)

    if decimal_comma:
        s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        # "1,234,567" thousands separators; but "12,5" (single comma, 1-2 digits) is a decimal comma
        decimal_like = s.str.match(r"^-?\d+,\d{1,2}$")
        s = s.where(~decimal_like, s.str.replace(",", ".", regex=False))
        s = s.str.replace(",", "", regex=False)

    out = pd.to_numeric(s, errors="coerce").fillna(0.0)
    out = out.where(~neg, -out.abs())
    return out


# ----------------------------------------------------------------------------
# Column mapping
# ----------------------------------------------------------------------------
def _map_columns(df: pd.DataFrame, warnings: List[str]) -> pd.DataFrame:
    norm_to_actual: Dict[str, str] = {}
    for col in df.columns:
        norm_to_actual.setdefault(_norm(col), col)

    mapping: Dict[str, str] = {}  # actual -> standard
    for standard, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            actual = norm_to_actual.get(alias)
            if actual is not None and actual not in mapping:
                mapping[actual] = standard
                break

    # Prefix fallbacks, e.g. "Cost (EUR)", "Conv. value (by conv. time)"
    def _fallback(standard: str, pattern: str) -> None:
        if standard in mapping.values():
            return
        rx = re.compile(pattern)
        for norm, actual in norm_to_actual.items():
            if actual not in mapping and rx.match(norm):
                mapping[actual] = standard
                return

    _fallback("cost", r"^(cost|spend)\b(?!\s*/)")
    _fallback("conversion_value", r"^(all )?conv(ersions?)?\.? value\b")
    _fallback("conversions", r"^(all )?conv(ersions?)?\.?(?!\s*(value|rate))\s*(\(.*\))?$")
    _fallback("impressions", r"^impr(essions?)?\.?$")

    # Query column missing -> guess the first mostly-text column
    if "query" not in mapping.values():
        guess = None
        for col in df.columns:
            if col in mapping:
                continue
            sample = df[col].astype(str).head(200)
            numeric_share = pd.to_numeric(
                sample.str.replace(r"[^\d.\-]", "", regex=True), errors="coerce"
            ).notna().mean()
            if numeric_share < 0.5 and sample.str.strip().ne("").mean() > 0.5:
                guess = col
                break
        if guess is None:
            raise CsvLoadError(
                "Could not find a search-term column. Make sure the CSV has a column named "
                "'Search term' (or 'Query') plus metrics like Impressions, Clicks and Cost. "
                f"Columns found: {', '.join(str(c) for c in df.columns[:12])}"
            )
        mapping[guess] = "query"
        warnings.append(f"No 'Search term' column found - using column '{guess}' as the search term.")

    renamed = df[list(mapping.keys())].rename(columns=mapping)
    return renamed.loc[:, ~renamed.columns.duplicated()].copy()


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------
def standardize_dataframe(df: pd.DataFrame, decimal_comma: bool = False) -> Tuple[pd.DataFrame, Dict]:
    """Map arbitrary headers to SearchPilot's internal schema and clean every value."""
    warnings: List[str] = []
    original_columns = [str(c) for c in df.columns]
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    df = _map_columns(df, warnings)

    # --- query text ------------------------------------------------------
    df["query"] = df["query"].astype(str).str.strip()
    before = len(df)
    junk = (
        df["query"].eq("")
        | df["query"].str.lower().isin({"nan", "none", "null", "--", "-"})
        | df["query"].str.match(r"(?i)^total\s*[:\-]")      # "Total: Account", "Total: Search"
        | df["query"].str.match(r"(?i)^total$")
    )
    df = df[~junk].copy()
    skipped = before - len(df)

    # --- text columns ----------------------------------------------------
    for col, default in (("campaign", "Default Campaign"), ("ad_group", "Default Ad Group"),
                         ("match_type", "Broad")):
        if col not in df.columns:
            df[col] = default
            warnings.append(f"No '{col.replace('_', ' ')}' column found - using '{default}'.")
        else:
            df[col] = df[col].astype(str).str.strip()
            df.loc[df[col].str.lower().isin({"", "nan", "none", "null", "--"}), col] = default

    # --- numeric columns -------------------------------------------------
    for col in NUMERIC_COLS:
        if col not in df.columns:
            df[col] = 0.0
            if col in ("impressions", "clicks", "cost"):
                warnings.append(f"No '{col}' column found - treating it as 0 for every row.")
        else:
            df[col] = _to_number(df[col], decimal_comma=decimal_comma)

    df["impressions"] = df["impressions"].round().clip(lower=0).astype("int64")
    df["clicks"] = df["clicks"].round().clip(lower=0).astype("int64")
    for col in ("cost", "conversions", "conversion_value"):
        df[col] = df[col].clip(lower=0).astype("float64")

    # Clicks can never exceed impressions in a real report; if impressions column is
    # missing/zero, derive a floor so CTR stays sane.
    df.loc[df["impressions"] < df["clicks"], "impressions"] = df["clicks"]

    if df.empty:
        raise CsvLoadError("No usable search-term rows were found in this file.")

    df = df[["query", "campaign", "ad_group", "match_type", "impressions", "clicks",
             "cost", "conversions", "conversion_value"]].reset_index(drop=True)

    info = {
        "original_columns": original_columns,
        "mapped_columns": list(df.columns),
        "skipped_rows": int(skipped),
        "warnings": warnings,
    }
    return df, info


def load_search_terms_csv(raw: bytes) -> Tuple[pd.DataFrame, Dict]:
    """Parse raw uploaded bytes into a clean standard DataFrame + info dict."""
    if not raw or not raw.strip():
        raise CsvLoadError("The file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise CsvLoadError("File is too large (limit is 200 MB).")

    text, encoding = _decode(raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    header_idx, delim = _detect_header(lines)
    body = "\n".join(lines[header_idx:])

    try:
        df = pd.read_csv(
            io.StringIO(body),
            sep=delim,
            dtype=str,
            keep_default_na=False,
            engine="python",
            on_bad_lines="skip",
            skip_blank_lines=True,
        )
    except Exception as exc:  # pandas ParserError, etc.
        raise CsvLoadError(f"Could not parse the file as a CSV table: {exc}") from exc

    if df.shape[1] < 2 and delim != "\t":
        # Single column usually means the wrong delimiter guess: retry by sniffing.
        try:
            dialect = csv.Sniffer().sniff(body[:20000], delimiters=",;\t|")
            df = pd.read_csv(io.StringIO(body), sep=dialect.delimiter, dtype=str,
                             keep_default_na=False, engine="python", on_bad_lines="skip")
            delim = dialect.delimiter
        except Exception:
            pass

    # Drop fully empty columns / rows (trailing delimiters in exports)
    df = df.loc[:, [c for c in df.columns if str(c).strip() and not str(c).startswith("Unnamed")]]
    df = df.dropna(how="all")
    if len(df) == 0:
        raise CsvLoadError("The file has headers but no data rows.")

    df, info = standardize_dataframe(df, decimal_comma=(delim == ";"))
    info.update({"encoding": encoding, "delimiter": {"\t": "tab"}.get(delim, delim),
                 "header_row": header_idx + 1})
    return df, info

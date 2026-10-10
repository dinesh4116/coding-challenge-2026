"""
AdCreative Intelligence - Data Ingestion & Validation Module
Handles ad performance CSV ingestion, rigorous validation, optional campaign fields,
interactive column mapping, data quality auditing, image-to-record matching,
and zero-safe metric calculations.
"""

import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from PIL import Image

REQUIRED_COLUMNS = ["ad_id", "spend", "impressions", "clicks", "conversions"]
OPTIONAL_COLUMNS = [
    "campaign_id",
    "campaign_name",
    "campaign",
    "audience",
    "placement",
    "date",
    "platform",
    "revenue",
    "conversion_value",
    "variant",
]
SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
NUMERIC_OPTIONAL_COLUMNS = ("revenue", "conversion_value")

COLUMN_SYNONYM_SUGGESTIONS: Dict[str, List[str]] = {
    "ad_id": ["ad_id", "adid", "creative_id", "creativeid", "asset_id", "ad_name", "creative_name", "id"],
    "spend": ["spend", "cost", "amount_spent", "ad_spend", "total_spend", "media_cost"],
    "impressions": ["impressions", "impr", "imps", "views", "ad_impressions"],
    "clicks": ["clicks", "link_clicks", "outbound_clicks", "ad_clicks", "total_clicks"],
    "conversions": ["conversions", "purchases", "leads", "results", "acquisitions", "conv", "orders"],
    "campaign_name": ["campaign_name", "campaign", "campaign_title"],
    "audience": ["audience", "ad_set", "adset_name", "targeting", "segment"],
    "placement": ["placement", "ad_placement", "position", "surface"],
    "platform": ["platform", "channel", "network", "publisher", "source"],
    "date": ["date", "day", "reporting_date", "stat_date"],
    "revenue": ["revenue", "conversion_value", "purchase_value", "sales", "total_revenue", "value"],
}


class IngestionValidationResult:
    def __init__(
        self,
        is_valid: bool,
        df: Optional[pd.DataFrame] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        matched_images: Optional[Dict[str, Any]] = None,
        unmatched_records: Optional[List[str]] = None,
        unmatched_images: Optional[List[str]] = None,
        excluded_records: Optional[List[Dict[str, Any]]] = None,
        available_optional_cols: Optional[List[str]] = None,
        uploaded_filenames: Optional[List[str]] = None,
        matched_filenames: Optional[Dict[str, str]] = None,
        matching_diagnostics: Optional[List[Dict[str, Any]]] = None,
    ):
        self.is_valid = is_valid
        self.df = df if df is not None else pd.DataFrame()
        self.errors = errors if errors is not None else []
        self.warnings = warnings if warnings is not None else []
        self.matched_images = matched_images if matched_images is not None else {}
        self.unmatched_records = unmatched_records if unmatched_records is not None else []
        self.unmatched_images = unmatched_images if unmatched_images is not None else []
        self.excluded_records = excluded_records if excluded_records is not None else []
        self.available_optional_cols = available_optional_cols if available_optional_cols is not None else []
        self.uploaded_filenames = uploaded_filenames if uploaded_filenames is not None else []
        self.matched_filenames = matched_filenames if matched_filenames is not None else {}
        self.matching_diagnostics = matching_diagnostics if matching_diagnostics is not None else []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "record_count": len(self.df),
            "matched_images_count": len(self.matched_images),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "unmatched_records": self.unmatched_records,
            "unmatched_images": self.unmatched_images,
            "excluded_records": self.excluded_records,
            "available_optional_cols": self.available_optional_cols,
            "uploaded_filenames": self.uploaded_filenames,
            "matched_filenames": self.matched_filenames,
            "matching_diagnostics": self.matching_diagnostics,
        }


def safe_divide(numerator: Optional[float], denominator: Optional[float], default: Optional[float] = None) -> Optional[float]:
    """Safely divides two numbers, returning default if denominator is zero, null, or NaN."""
    if denominator is None or np.isnan(denominator) or denominator <= 0:
        return default
    if numerator is None or np.isnan(numerator):
        return default
    return float(numerator) / float(denominator)


def suggest_column_mapping(raw_columns: List[str]) -> Dict[str, Optional[str]]:
    """
    Given a list of raw CSV column names, suggests mappings to standard schema columns
    (ad_id, spend, impressions, clicks, conversions, campaign_name, audience, placement, platform, date, revenue).
    Returns a dict {target_schema_col: matched_raw_col_or_None}.
    """
    norm_to_orig: Dict[str, str] = {}
    for col in raw_columns:
        clean_key = re.sub(r"[\s\-]+", "_", str(col).strip().lower())
        if clean_key not in norm_to_orig:
            norm_to_orig[clean_key] = str(col)

    suggestions: Dict[str, Optional[str]] = {}
    used_orig = set()
    for target_col, synonyms in COLUMN_SYNONYM_SUGGESTIONS.items():
        matched_orig = None
        for syn in synonyms:
            if syn in norm_to_orig and norm_to_orig[syn] not in used_orig:
                matched_orig = norm_to_orig[syn]
                break
        suggestions[target_col] = matched_orig
        if matched_orig is not None:
            used_orig.add(matched_orig)
    return suggestions


def apply_column_mapping(df: pd.DataFrame, column_map: Dict[str, str]) -> pd.DataFrame:
    """
    Renames columns in `df` according to `column_map` where keys are target schema column names
    (e.g. 'ad_id', 'spend') and values are source column names in `df` (or vice versa).
    Does not mutate the input DataFrame.
    """
    if df is None or df.empty or not column_map:
        return df.copy() if df is not None else pd.DataFrame()

    out = df.copy()
    existing_cols = set(out.columns)
    rename_dict: Dict[str, str] = {}

    all_targets = set(REQUIRED_COLUMNS) | set(OPTIONAL_COLUMNS)
    for k, v in column_map.items():
        if not k or not v or k == v or v == "(None / Not Present)" or k == "(None / Not Present)":
            continue
        # Case 1: {target_schema_col: source_col_in_df}
        if k in all_targets and v in existing_cols:
            rename_dict[v] = k
        # Case 2: {source_col_in_df: target_schema_col}
        elif k in existing_cols and v in all_targets:
            rename_dict[k] = v

    if rename_dict:
        out = out.rename(columns=rename_dict)
    return out


def compute_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes CTR, CVR, CPC, CPA (and ROAS when revenue/conversion_value is present)
    for each row safely handling zero denominators.
    CTR = clicks / impressions
    CVR = conversions / clicks
    CPC = spend / clicks
    CPA = spend / conversions
    ROAS = revenue / spend (only when revenue or conversion_value column is present)
    Undefined metrics are represented as np.nan (never 0.0).
    """
    df = df.copy()

    with np.errstate(divide="ignore", invalid="ignore"):
        imp = df["impressions"].astype(float)
        clk = df["clicks"].astype(float)
        spn = df["spend"].astype(float)
        cnv = df["conversions"].astype(float)

        df["ctr"] = np.where(imp > 0, clk / imp, np.nan)
        df["cvr"] = np.where(clk > 0, cnv / clk, np.nan)
        df["cpc"] = np.where(clk > 0, spn / clk, np.nan)
        df["cpa"] = np.where(cnv > 0, spn / cnv, np.nan)

        rev_col = "revenue" if "revenue" in df.columns else ("conversion_value" if "conversion_value" in df.columns else None)
        if rev_col is not None:
            rev = pd.to_numeric(df[rev_col], errors="coerce").astype(float)
            df["revenue"] = rev
            df["roas"] = np.where((spn > 0) & (~np.isnan(rev)), rev / spn, np.nan)

    return df


def validate_and_parse_csv(
    csv_file_or_path_or_bytes: Any,
    allow_view_through_conversions: bool = False,
    column_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[pd.DataFrame], List[str], List[str]]:
    """
    Validates CSV columns, formats, nulls, duplicates, and domain constraints.
    Accepts file paths, raw bytes, file-like streams, or an already-loaded pd.DataFrame.
    Returns: (cleaned_df, errors, warnings)
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        if isinstance(csv_file_or_path_or_bytes, pd.DataFrame):
            df = csv_file_or_path_or_bytes.copy()
        elif isinstance(csv_file_or_path_or_bytes, (str, Path)):
            df = pd.read_csv(csv_file_or_path_or_bytes)
        elif isinstance(csv_file_or_path_or_bytes, bytes):
            df = pd.read_csv(io.BytesIO(csv_file_or_path_or_bytes))
        elif hasattr(csv_file_or_path_or_bytes, "read"):
            if hasattr(csv_file_or_path_or_bytes, "seek"):
                csv_file_or_path_or_bytes.seek(0)
            df = pd.read_csv(csv_file_or_path_or_bytes)
            if hasattr(csv_file_or_path_or_bytes, "seek"):
                csv_file_or_path_or_bytes.seek(0)
        else:
            errors.append("Invalid CSV input source provided.")
            return None, errors, warnings
    except Exception as e:
        errors.append(f"Failed to parse CSV file: {str(e)}")
        return None, errors, warnings

    if df.empty:
        errors.append("CSV file is completely empty.")
        return None, errors, warnings

    # Apply user-specified column mapping if provided prior to normalization
    if column_mapping:
        df = apply_column_mapping(df, column_mapping)

    # Normalize column names: lowercase, strip whitespace
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Harmonize 'campaign' alias with 'campaign_name' so both work seamlessly
    if "campaign" in df.columns and "campaign_name" not in df.columns:
        df["campaign_name"] = df["campaign"]
    elif "campaign_name" in df.columns and "campaign" not in df.columns:
        df["campaign"] = df["campaign_name"]

    # Check required columns
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required column(s): {', '.join(missing_cols)}")
        return None, errors, warnings

    # Detect available optional columns
    present_optional = [c for c in OPTIONAL_COLUMNS if c in df.columns]
    if present_optional:
        warnings.append(f"Detected optional campaign metadata column(s): {', '.join(present_optional)}")

    # Check for empty or null ad_id
    if df["ad_id"].isna().any():
        null_count = int(df["ad_id"].isna().sum())
        errors.append(f"Found {null_count} record(s) with missing or empty 'ad_id'.")

    # Clean ad_id to string and strip
    df["ad_id"] = df["ad_id"].astype(str).str.strip()

    # Empty string ad_id check
    empty_id_mask = df["ad_id"] == ""
    if empty_id_mask.any():
        errors.append(f"Found {int(empty_id_mask.sum())} record(s) with blank 'ad_id'.")

    # Check duplicates
    duplicate_mask = df["ad_id"].duplicated(keep=False)
    if duplicate_mask.any():
        dups = df.loc[duplicate_mask, "ad_id"].unique().tolist()
        errors.append(f"Found duplicate ad_id(s): {', '.join(dups[:5])}{'...' if len(dups) > 5 else ''}")

    # Numeric conversion & validation
    numeric_cols = ["spend", "impressions", "clicks", "conversions"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        nan_count = int(df[col].isna().sum())
        if nan_count > 0:
            errors.append(f"Column '{col}' has {nan_count} non-numeric or missing value(s).")
        else:
            neg_count = int((df[col] < 0).sum())
            if neg_count > 0:
                errors.append(f"Column '{col}' contains {neg_count} negative value(s). Metrics cannot be negative.")

    # Optional numeric revenue / conversion_value validation
    for rev_col in NUMERIC_OPTIONAL_COLUMNS:
        if rev_col in df.columns:
            df[rev_col] = pd.to_numeric(df[rev_col], errors="coerce")
            rev_nan = int(df[rev_col].isna().sum())
            if rev_nan > 0:
                warnings.append(f"Optional column '{rev_col}' has {rev_nan} missing/non-numeric value(s) (ROAS will be undefined for those rows).")
            neg_rev = int((df[rev_col].dropna() < 0).sum())
            if neg_rev > 0:
                errors.append(f"Column '{rev_col}' contains {neg_rev} negative value(s). Revenue cannot be negative.")

    if errors:
        return None, errors, warnings

    # Domain logical validation: clicks cannot exceed impressions (even when impressions == 0)
    click_violations = df["clicks"] > df["impressions"]
    if click_violations.any():
        count = int(click_violations.sum())
        violating_ids = df.loc[click_violations, "ad_id"].tolist()[:3]
        errors.append(
            f"{count} record(s) have clicks exceeding impressions, which is impossible (e.g. {', '.join(violating_ids)})."
        )

    # Conversions cannot exceed clicks (unless view-through conversions explicitly enabled)
    conv_violations = df["conversions"] > df["clicks"]
    if conv_violations.any():
        count = int(conv_violations.sum())
        violating_ids = df.loc[conv_violations, "ad_id"].tolist()[:3]
        if not allow_view_through_conversions:
            errors.append(
                f"{count} record(s) have conversions exceeding clicks, which is impossible for click-through attribution (e.g. {', '.join(violating_ids)})."
            )
        else:
            warnings.append(
                f"{count} record(s) have conversions exceeding clicks. Permitted under view-through / post-impression attribution mode."
            )

    if errors:
        return None, errors, warnings

    # Non-integer event count check
    for count_col in ["impressions", "clicks", "conversions"]:
        if (df[count_col] % 1 != 0).any():
            warnings.append(f"Column '{count_col}' contains fractional (non-integer) event counts.")

    # Spend > 0 with 0 impressions warning
    spend_zero_imp = int(((df["spend"] > 0) & (df["impressions"] == 0)).sum())
    if spend_zero_imp > 0:
        warnings.append(f"{spend_zero_imp} record(s) report positive spend (> $0) with 0 impressions.")

    # Zero spend with positive revenue warning
    if "revenue" in df.columns or "conversion_value" in df.columns:
        r_col = "revenue" if "revenue" in df.columns else "conversion_value"
        zero_spend_rev = int(((df["spend"] == 0) & (df[r_col].fillna(0) > 0)).sum())
        if zero_spend_rev > 0:
            warnings.append(f"{zero_spend_rev} record(s) have 0 spend (ROAS will be undefined / unavailable for 0-spend rows).")

    # Zero impressions warning
    zero_imp = int((df["impressions"] == 0).sum())
    if zero_imp > 0:
        warnings.append(f"{zero_imp} record(s) have 0 impressions (CTR will be undefined / unavailable).")

    # Zero clicks warning
    zero_clk = int((df["clicks"] == 0).sum())
    if zero_clk > 0:
        warnings.append(f"{zero_clk} record(s) have 0 clicks (CVR and CPC will be undefined / unavailable).")

    # Zero conversions warning
    zero_cnv = int((df["conversions"] == 0).sum())
    if zero_cnv > 0:
        warnings.append(f"{zero_cnv} record(s) have 0 conversions (CPA will be undefined / unavailable).")

    # Clean optional text columns if present (excluding numeric revenue/value columns)
    for opt_col in present_optional:
        if opt_col in df.columns and opt_col not in NUMERIC_OPTIONAL_COLUMNS:
            df[opt_col] = df[opt_col].fillna("Unknown").astype(str).str.strip()

    # Compute derived metrics safely
    df = compute_derived_metrics(df)

    return df, errors, warnings


def normalize_identifier_candidates(raw_value: Any) -> List[str]:
    """
    Produces an ordered list of normalized candidate keys for matching CSV ad_id values
    against uploaded image filenames across PNG, JPG, JPEG, and WEBP formats.
    Handles:
      - Path prefixes (e.g., 'images/ad_warm_01.png' -> 'ad_warm_01.png')
      - Leading/trailing whitespace and case differences (' AD_WARM_01.JPG ' -> 'ad_warm_01')
      - Single or repeated image extensions ('ad_warm_01.png.jpg' -> 'ad_warm_01')
      - OS/browser duplicate download suffixes ('ad_warm_01 (1).png', 'ad_warm_01 - Copy.png' -> 'ad_warm_01')
      - Hyphen/space/underscore variations ('ad-warm-01' <-> 'ad_warm_01')
    """
    raw_str = str(raw_value or "").strip()
    if not raw_str:
        return []

    base_name = Path(raw_str.replace("\\", "/")).name.strip()
    lower_name = base_name.lower()

    # Strip one or more supported image extensions (.png, .jpg, .jpeg, .webp)
    stem_no_ext = re.sub(r"(\.(png|jpg|jpeg|webp))+$", "", lower_name, flags=re.IGNORECASE).strip()
    path_stem = Path(lower_name).stem.strip()

    # Strip duplicate download suffixes such as " (1)", " (2)", "-copy", "_copy"
    stem_no_copy = re.sub(r"\s*(\(\d+\)|[-_]\s*copy|\s+copy)$", "", stem_no_ext, flags=re.IGNORECASE).strip()

    # Normalize separators (spaces, hyphens, underscores -> single underscore)
    canonical_sep = re.sub(r"[\s\-_]+", "_", stem_no_copy).strip("_")

    # Alphanumeric-only fallback
    alnum_only = re.sub(r"[^a-z0-9]", "", stem_no_copy)

    candidates: List[str] = []
    for cand in (lower_name, stem_no_ext, path_stem, stem_no_copy, canonical_sep, alnum_only):
        if cand and cand not in candidates:
            candidates.append(cand)
    return candidates


def ensure_persistent_image(img_obj: Any) -> Any:
    """
    Converts transient file streams (such as Streamlit UploadedFile objects) or file paths
    into durable in-memory PIL.Image.Image copies so images remain accessible across page navigations.
    If an uploaded stream contains corrupt image bytes, returns the raw bytes so feature extraction
    can report an explicit extraction error status rather than silently dropping it.
    """
    if isinstance(img_obj, Image.Image):
        try:
            img_obj.load()
            return img_obj.copy()
        except Exception:
            return img_obj

    if isinstance(img_obj, (bytes, bytearray)):
        raw_bytes = bytes(img_obj)
        try:
            with Image.open(io.BytesIO(raw_bytes)) as im:
                im.load()
                return im.copy()
        except Exception:
            return raw_bytes

    if isinstance(img_obj, (str, Path)):
        p = Path(img_obj)
        if p.exists() and p.is_file():
            try:
                with Image.open(p) as im:
                    im.load()
                    return im.copy()
            except Exception:
                return img_obj
        return img_obj

    if hasattr(img_obj, "getvalue") or hasattr(img_obj, "read"):
        raw_bytes = b""
        try:
            if hasattr(img_obj, "getvalue"):
                raw_bytes = img_obj.getvalue()
            else:
                if hasattr(img_obj, "seek"):
                    img_obj.seek(0)
                raw_bytes = img_obj.read()
                if hasattr(img_obj, "seek"):
                    img_obj.seek(0)
            if isinstance(raw_bytes, str):
                raw_bytes = raw_bytes.encode("utf-8")
            with Image.open(io.BytesIO(raw_bytes)) as im:
                im.load()
                return im.copy()
        except Exception:
            return raw_bytes if raw_bytes else img_obj

    return img_obj


def _extract_raw_image_entries(images_dict_or_list: Any) -> List[Tuple[str, Any]]:
    """Normalizes dict or list/tuple of uploaded images into [(filename, image_object), ...]."""
    entries: List[Tuple[str, Any]] = []
    if images_dict_or_list is None:
        return entries
    if isinstance(images_dict_or_list, dict):
        for fname, img_obj in images_dict_or_list.items():
            entries.append((str(fname).strip(), img_obj))
    elif isinstance(images_dict_or_list, (list, tuple)):
        for item in images_dict_or_list:
            if hasattr(item, "name"):
                name_str = str(item.name).strip()
            else:
                name_str = str(item).strip()
            entries.append((name_str, item))
    return entries


def match_images_to_records(
    df: pd.DataFrame,
    images_dict_or_list: Any,
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """
    Matches uploaded images to CSV ad_id records.
    Supports PNG, JPG, JPEG, and WEBP.
    Handles mismatched case, extensions, whitespace, hyphens/underscores, and duplicate suffixes,
    and stores durable in-memory PIL images so they persist across Streamlit page navigations.
    """
    matched: Dict[str, Any] = {}
    unmatched_records: List[str] = []
    unmatched_images: List[str] = []

    entries = _extract_raw_image_entries(images_dict_or_list)
    norm_images: Dict[str, Tuple[str, Any]] = {}

    for orig_name, raw_obj in entries:
        persistent_obj = ensure_persistent_image(raw_obj)
        for cand_key in normalize_identifier_candidates(orig_name):
            # Preserve first exact match if multiple keys map to same bucket
            if cand_key not in norm_images:
                norm_images[cand_key] = (orig_name, persistent_obj)

    used_image_names = set()

    for ad_id in df["ad_id"]:
        ad_id_str = str(ad_id).strip()
        matched_entry: Optional[Tuple[str, Any]] = None
        for cand_key in normalize_identifier_candidates(ad_id_str):
            if cand_key in norm_images:
                matched_entry = norm_images[cand_key]
                break

        if matched_entry is not None:
            orig_name, obj = matched_entry
            matched[str(ad_id)] = obj
            used_image_names.add(orig_name)
        else:
            unmatched_records.append(str(ad_id))

    for orig_name, _ in entries:
        if orig_name not in used_image_names:
            unmatched_images.append(orig_name)

    return matched, unmatched_records, unmatched_images


def ingest_ad_dataset(
    csv_input: Any,
    images_input: Any,
    allow_view_through_conversions: bool = False,
    column_mapping: Optional[Dict[str, str]] = None,
) -> IngestionValidationResult:
    """
    Complete ingestion pipeline: parses CSV, validates, matches images,
    builds diagnostic matching metadata, and returns an IngestionValidationResult.
    """
    df, errors, warnings = validate_and_parse_csv(
        csv_input,
        allow_view_through_conversions=allow_view_through_conversions,
        column_mapping=column_mapping,
    )
    if errors or df is None:
        return IngestionValidationResult(is_valid=False, df=df, errors=errors, warnings=warnings)

    entries = _extract_raw_image_entries(images_input)
    uploaded_filenames = [name for name, _ in entries]

    matched_images, unmatched_recs, unmatched_imgs = match_images_to_records(df, images_input)

    # Map each matched ad_id back to its matched filename and build diagnostics for all rows
    norm_filename_lookup: Dict[str, str] = {}
    for orig_name, _ in entries:
        for cand in normalize_identifier_candidates(orig_name):
            if cand not in norm_filename_lookup:
                norm_filename_lookup[cand] = orig_name

    matched_filenames: Dict[str, str] = {}
    matching_diagnostics: List[Dict[str, Any]] = []

    for ad_id in df["ad_id"]:
        ad_str = str(ad_id)
        cands = normalize_identifier_candidates(ad_str)
        expected_stem = cands[1] if len(cands) > 1 else (cands[0] if cands else ad_str.strip().lower())
        matched_fname = None
        for c in cands:
            if c in norm_filename_lookup:
                matched_fname = norm_filename_lookup[c]
                break

        uploaded_summary = ", ".join(uploaded_filenames) if uploaded_filenames else "None (0 image files uploaded)"
        if ad_str in matched_images and matched_fname is not None:
            matched_filenames[ad_str] = matched_fname
            matching_diagnostics.append({
                "ad_id": ad_str,
                "csv_ad_id": ad_str,
                "expected_filename_stem": expected_stem,
                "status": "Matched",
                "match_status": "Matched",
                "matched_filename": matched_fname,
                "uploaded_filenames": uploaded_summary,
                "diagnostic": f"Matched CSV ad_id '{ad_str}' to uploaded file '{matched_fname}'.",
            })
        else:
            if not uploaded_filenames:
                diag_msg = (
                    f"No image files were uploaded. Expected an image named '{expected_stem}.png' "
                    f"(or .jpg / .jpeg / .webp) for CSV ad_id '{ad_str}'."
                )
            else:
                preview_files = ", ".join(uploaded_filenames[:8]) + ("..." if len(uploaded_filenames) > 8 else "")
                diag_msg = (
                    f"No uploaded file stem matched CSV ad_id '{ad_str}' (expected stem '{expected_stem}'). "
                    f"Uploaded files ({len(uploaded_filenames)}): [{preview_files}]"
                )
            matching_diagnostics.append({
                "ad_id": ad_str,
                "csv_ad_id": ad_str,
                "expected_filename_stem": expected_stem,
                "status": "Missing Image",
                "match_status": "Missing Image",
                "matched_filename": None,
                "uploaded_filenames": uploaded_summary,
                "diagnostic": diag_msg,
            })

    if unmatched_recs:
        if not uploaded_filenames:
            warnings.append(
                f"{len(unmatched_recs)} CSV ad record(s) have no matched images because 0 image files were uploaded "
                f"(missing: {', '.join(unmatched_recs[:5])}{'...' if len(unmatched_recs) > 5 else ''})."
            )
        else:
            warnings.append(
                f"{len(unmatched_recs)} ad record(s) lack matching image files: {', '.join(unmatched_recs[:5])}{'...' if len(unmatched_recs) > 5 else ''}"
            )
    if unmatched_imgs:
        warnings.append(
            f"{len(unmatched_imgs)} uploaded image(s) do not match any ad_id in CSV: {', '.join(unmatched_imgs[:5])}{'...' if len(unmatched_imgs) > 5 else ''}"
        )

    present_optional = [c for c in OPTIONAL_COLUMNS if c in df.columns]

    return IngestionValidationResult(
        is_valid=True,
        df=df,
        errors=errors,
        warnings=warnings,
        matched_images=matched_images,
        unmatched_records=unmatched_recs,
        unmatched_images=unmatched_imgs,
        available_optional_cols=present_optional,
        uploaded_filenames=uploaded_filenames,
        matched_filenames=matched_filenames,
        matching_diagnostics=matching_diagnostics,
    )


def compute_data_quality_summary(
    df: Optional[pd.DataFrame],
    ingestion_result: Optional[IngestionValidationResult] = None,
    is_synthetic: bool = False,
) -> Dict[str, Any]:
    """
    Computes a comprehensive Data Quality audit for the Executive Overview and Export Center:
    - Number of distinct creatives and performance records
    - Matched vs. missing creative images
    - Date coverage and freshness (when valid date column exists; never fabricated when absent)
    - Present and missing optional schema fields
    - Zero-denominator counts (0 impressions, 0 clicks, 0 conversions, 0 spend)
    - Explicit dataset lineage (DEMO DATA — SYNTHETIC EXAMPLE vs. IMPORTED EMPIRICAL DATASET)
    """
    if df is None or df.empty:
        return {
            "record_count": 0,
            "creative_count": 0,
            "matched_image_count": 0,
            "missing_image_count": 0,
            "has_dates": False,
            "min_date": None,
            "max_date": None,
            "distinct_dates": 0,
            "date_coverage_label": "Unavailable (No dataset loaded)",
            "data_freshness": "Unknown (No dataset loaded)",
            "present_required_fields": [],
            "present_optional_fields": [],
            "missing_optional_fields": list(OPTIONAL_COLUMNS),
            "zero_impressions_count": 0,
            "zero_clicks_count": 0,
            "zero_conversions_count": 0,
            "zero_spend_count": 0,
            "is_synthetic": is_synthetic,
            "dataset_origin": "No Dataset Loaded",
        }

    rec_count = len(df)
    creative_count = int(df["ad_id"].astype(str).nunique()) if "ad_id" in df.columns else rec_count

    if ingestion_result is not None:
        matched_img_count = len(ingestion_result.matched_images)
        missing_img_count = len(ingestion_result.unmatched_records)
    elif "extraction_status" in df.columns:
        matched_img_count = int((df["extraction_status"] == "success").sum())
        missing_img_count = max(0, creative_count - matched_img_count)
    else:
        matched_img_count = 0
        missing_img_count = creative_count

    # Date coverage
    has_dates = False
    min_date_str: Optional[str] = None
    max_date_str: Optional[str] = None
    distinct_dates = 0
    date_coverage_label = "Not Collected (No valid 'date' column in CSV)"
    data_freshness = "Unknown (Static snapshot without timestamps)"

    if "date" in df.columns:
        parsed_dt = pd.to_datetime(df["date"].replace(["Unknown", "None", "nan", ""], np.nan), errors="coerce").dropna()
        if not parsed_dt.empty:
            has_dates = True
            min_date_str = parsed_dt.min().strftime("%Y-%m-%d")
            max_date_str = parsed_dt.max().strftime("%Y-%m-%d")
            distinct_dates = int(parsed_dt.dt.date.nunique())
            date_coverage_label = f"{min_date_str} to {max_date_str} ({distinct_dates} distinct date{'s' if distinct_dates != 1 else ''})"
            data_freshness = f"Latest record date: {max_date_str} ({'Synthetic benchmark dates' if is_synthetic else 'Imported campaign dates'})"

    present_req = [c for c in REQUIRED_COLUMNS if c in df.columns]
    canonical_optional = ["campaign_id", "campaign_name", "audience", "placement", "platform", "date", "revenue", "variant"]
    present_opt = [c for c in canonical_optional if c in df.columns and df[c].replace(["Unknown", "nan", ""], np.nan).notna().any()]
    missing_opt = [c for c in canonical_optional if c not in present_opt]

    zero_imp = int((pd.to_numeric(df["impressions"], errors="coerce").fillna(0) == 0).sum()) if "impressions" in df.columns else 0
    zero_clk = int((pd.to_numeric(df["clicks"], errors="coerce").fillna(0) == 0).sum()) if "clicks" in df.columns else 0
    zero_cnv = int((pd.to_numeric(df["conversions"], errors="coerce").fillna(0) == 0).sum()) if "conversions" in df.columns else 0
    zero_spn = int((pd.to_numeric(df["spend"], errors="coerce").fillna(0) == 0).sum()) if "spend" in df.columns else 0

    origin_lbl = "DEMO DATA — SYNTHETIC EXAMPLE" if is_synthetic else "IMPORTED EMPIRICAL DATASET"
    return {
        "record_count": rec_count,
        "performance_record_count": rec_count,
        "creative_count": creative_count,
        "matched_image_count": matched_img_count,
        "missing_image_count": missing_img_count,
        "has_dates": has_dates,
        "min_date": min_date_str,
        "max_date": max_date_str,
        "distinct_dates": distinct_dates,
        "date_coverage_label": date_coverage_label,
        "date_coverage": date_coverage_label,
        "data_freshness": data_freshness,
        "present_required_fields": present_req,
        "present_optional_fields": present_opt,
        "missing_optional_fields": missing_opt,
        "zero_impressions_count": zero_imp,
        "zero_impression_creatives": zero_imp,
        "zero_clicks_count": zero_clk,
        "zero_click_creatives": zero_clk,
        "zero_conversions_count": zero_cnv,
        "zero_conversion_creatives": zero_cnv,
        "zero_spend_count": zero_spn,
        "is_synthetic": bool(is_synthetic),
        "dataset_origin": origin_lbl,
        "dataset_origin_label": origin_lbl,
    }


def generate_example_csv_content(include_optional: bool = True) -> str:
    """
    Generates downloadable sample CSV content meeting all specifications,
    including both required performance fields and optional campaign/audience/placement fields.
    """
    sample_data = [
        {
            "ad_id": "ad_warm_01",
            "campaign_id": "cmp_summer_2026",
            "campaign_name": "Summer Direct Response",
            "audience": "High-Intent Shoppers (25-45)",
            "placement": "Instagram Feed",
            "platform": "Meta",
            "date": "2026-06-01",
            "spend": 620.00,
            "impressions": 34000,
            "clicks": 1054,
            "conversions": 58,
        },
        {
            "ad_id": "ad_warm_02",
            "campaign_id": "cmp_summer_2026",
            "campaign_name": "Summer Direct Response",
            "audience": "Skincare Retargeting",
            "placement": "Facebook Feed",
            "platform": "Meta",
            "date": "2026-06-02",
            "spend": 580.00,
            "impressions": 31000,
            "clicks": 930,
            "conversions": 52,
        },
        {
            "ad_id": "ad_warm_03",
            "campaign_id": "cmp_growth_2026",
            "campaign_name": "Story Acquisition Sprint",
            "audience": "Broad Lifestyle & Beauty",
            "placement": "Instagram Story / Reel",
            "platform": "Instagram",
            "date": "2026-06-03",
            "spend": 710.00,
            "impressions": 39000,
            "clicks": 1287,
            "conversions": 72,
        },
        {
            "ad_id": "ad_warm_04",
            "campaign_id": "cmp_summer_2026",
            "campaign_name": "Summer Direct Response",
            "audience": "High-Intent Shoppers (25-45)",
            "placement": "Instagram Feed",
            "platform": "Meta",
            "date": "2026-06-04",
            "spend": 450.00,
            "impressions": 25000,
            "clicks": 625,
            "conversions": 28,
        },
        {
            "ad_id": "ad_cool_01",
            "campaign_id": "cmp_b2b_saas",
            "campaign_name": "SaaS Enterprise Push",
            "audience": "IT Decision Makers",
            "placement": "Desktop Feed",
            "platform": "LinkedIn",
            "date": "2026-06-05",
            "spend": 650.00,
            "impressions": 36000,
            "clicks": 720,
            "conversions": 26,
        },
        {
            "ad_id": "ad_cool_02",
            "campaign_id": "cmp_b2b_saas",
            "campaign_name": "SaaS Enterprise Push",
            "audience": "Engineering Leads",
            "placement": "Display Network",
            "platform": "Google Ads",
            "date": "2026-06-06",
            "spend": 590.00,
            "impressions": 32000,
            "clicks": 576,
            "conversions": 20,
        },
        {
            "ad_id": "ad_neut_01",
            "campaign_id": "cmp_luxury_brand",
            "campaign_name": "Minimalist Showcase",
            "audience": "Luxury Accessories",
            "placement": "Instagram Feed",
            "platform": "Meta",
            "date": "2026-06-07",
            "spend": 520.00,
            "impressions": 28000,
            "clicks": 560,
            "conversions": 22,
        },
        {
            "ad_id": "ad_neut_02",
            "campaign_id": "cmp_luxury_brand",
            "campaign_name": "Minimalist Showcase",
            "audience": "Modern Wardrobe Lookalike",
            "placement": "Facebook Feed",
            "platform": "Meta",
            "date": "2026-06-08",
            "spend": 630.00,
            "impressions": 34000,
            "clicks": 884,
            "conversions": 44,
        },
    ]

    df = pd.DataFrame(sample_data)
    if not include_optional:
        df = df[REQUIRED_COLUMNS]
    return df.to_csv(index=False)

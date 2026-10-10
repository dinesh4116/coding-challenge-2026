"""
AdCreative Intelligence - Data Ingestion & Validation Module
Handles ad performance CSV ingestion, rigorous validation, optional campaign fields,
image-to-record matching, and zero-safe metric calculations.
"""

import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from PIL import Image

REQUIRED_COLUMNS = ["ad_id", "spend", "impressions", "clicks", "conversions"]
OPTIONAL_COLUMNS = ["campaign_id", "campaign_name", "audience", "placement", "date", "platform"]


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
        }


def safe_divide(numerator: Optional[float], denominator: Optional[float], default: Optional[float] = None) -> Optional[float]:
    """Safely divides two numbers, returning default if denominator is zero, null, or NaN."""
    if denominator is None or np.isnan(denominator) or denominator <= 0:
        return default
    if numerator is None or np.isnan(numerator):
        return default
    return float(numerator) / float(denominator)


def compute_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes CTR, CVR, CPC, CPA for each row safely handling zero denominators.
    CTR = clicks / impressions
    CVR = conversions / clicks
    CPC = spend / clicks
    CPA = spend / conversions
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

    return df


def validate_and_parse_csv(
    csv_file_or_path_or_bytes: Any,
    allow_view_through_conversions: bool = False,
) -> Tuple[Optional[pd.DataFrame], List[str], List[str]]:
    """
    Validates CSV columns, formats, nulls, duplicates, and domain constraints.
    Returns: (cleaned_df, errors, warnings)
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        if isinstance(csv_file_or_path_or_bytes, (str, Path)):
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

    # Normalize column names: lowercase, strip whitespace
    df.columns = [str(c).strip().lower() for c in df.columns]

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
        raw_vals = df[col].copy()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        nan_count = int(df[col].isna().sum())
        if nan_count > 0:
            errors.append(f"Column '{col}' has {nan_count} non-numeric or missing value(s).")
        else:
            neg_count = int((df[col] < 0).sum())
            if neg_count > 0:
                errors.append(f"Column '{col}' contains {neg_count} negative value(s). Metrics cannot be negative.")

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

    # Clean optional text columns if present
    for opt_col in present_optional:
        if opt_col in df.columns:
            df[opt_col] = df[opt_col].fillna("Unknown").astype(str).str.strip()

    # Compute derived metrics safely
    df = compute_derived_metrics(df)

    return df, errors, warnings


def match_images_to_records(
    df: pd.DataFrame,
    images_dict_or_list: Any,
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """
    Matches uploaded images to CSV ad_id records.
    images_dict_or_list can be:
      - dict: {filename: PIL.Image or filepath or bytes}
      - list: list of filepaths or UploadedFile objects (having .name)
    Matching logic:
      Matches ad_id with filename stem (without extension), case-insensitive and stripped.
      Also handles direct ad_id == filename.
    """
    matched: Dict[str, Any] = {}
    unmatched_records: List[str] = []
    unmatched_images: List[str] = []

    norm_images: Dict[str, Tuple[str, Any]] = {}

    if isinstance(images_dict_or_list, dict):
        for fname, img_obj in images_dict_or_list.items():
            name_str = str(fname)
            stem = Path(name_str).stem.strip().lower()
            norm_images[stem] = (name_str, img_obj)
            norm_images[name_str.strip().lower()] = (name_str, img_obj)
    elif isinstance(images_dict_or_list, (list, tuple)):
        for item in images_dict_or_list:
            if hasattr(item, "name"):
                name_str = item.name
            else:
                name_str = str(item)
            stem = Path(name_str).stem.strip().lower()
            norm_images[stem] = (name_str, item)
            norm_images[name_str.strip().lower()] = (name_str, item)

    used_image_names = set()

    for ad_id in df["ad_id"]:
        ad_key = str(ad_id).strip().lower()
        ad_stem = Path(ad_key).stem

        if ad_key in norm_images:
            orig_name, obj = norm_images[ad_key]
            matched[str(ad_id)] = obj
            used_image_names.add(orig_name)
        elif ad_stem in norm_images:
            orig_name, obj = norm_images[ad_stem]
            matched[str(ad_id)] = obj
            used_image_names.add(orig_name)
        else:
            unmatched_records.append(str(ad_id))

    all_raw_names = set()
    if isinstance(images_dict_or_list, dict):
        all_raw_names = set(images_dict_or_list.keys())
    elif isinstance(images_dict_or_list, (list, tuple)):
        for item in images_dict_or_list:
            all_raw_names.add(item.name if hasattr(item, "name") else str(item))

    for raw_name in all_raw_names:
        if raw_name not in used_image_names:
            unmatched_images.append(raw_name)

    return matched, unmatched_records, unmatched_images


def ingest_ad_dataset(
    csv_input: Any,
    images_input: Any,
    allow_view_through_conversions: bool = False,
) -> IngestionValidationResult:
    """
    Complete ingestion pipeline: parses CSV, validates, matches images,
    identifies available optional metadata columns, and returns an IngestionValidationResult.
    """
    df, errors, warnings = validate_and_parse_csv(
        csv_input,
        allow_view_through_conversions=allow_view_through_conversions,
    )
    if errors or df is None:
        return IngestionValidationResult(is_valid=False, df=df, errors=errors, warnings=warnings)

    matched_images, unmatched_recs, unmatched_imgs = match_images_to_records(df, images_input)

    if unmatched_recs:
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
    )


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

from io import BytesIO
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse


# ==================================================
# 1. FASTAPI APPLICATION
# ==================================================

app = FastAPI(
    title="PS-01 Search Term Triage Engine",
    description=(
        "Uncertainty-aware search-term classification "
        "with human review and explainable decisions."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# 2. COLUMN ALIASES
# ==================================================

ALIASES = {
    "query": [
        "query",
        "query_text",
        "search_term",
        "search_query",
        "keyword",
        "term",
    ],
    "impressions": ["impressions", "impression"],
    "clicks": ["clicks", "click"],
    "cost": ["cost", "spend", "total_cost"],
    "conversions": ["conversions", "conversion"],
    "conversion_value": [
        "conversion_value",
        "conversion_value_inr",
        "revenue",
        "value",
    ],
}


# ==================================================
# 3. NORMALIZE COLUMN NAMES
# ==================================================

def normalize_column(name: Any) -> str:
    """Normalize column names for consistent processing."""

    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


# ==================================================
# 4. VALIDATE AND PREPARE THE DATASET
# ==================================================

def prepare_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Validate required fields and standardize CSV columns."""

    if df.empty:
        raise ValueError("The uploaded CSV contains no data rows.")

    df.columns = [normalize_column(column) for column in df.columns]

    rename_map = {}

    for standard_name, aliases in ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = standard_name
                break

    df = df.rename(columns=rename_map)

    required_columns = [
        "query",
        "impressions",
        "clicks",
        "cost",
        "conversions",
        "conversion_value",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
            + ". Required fields include query_text, impressions, "
            "clicks, cost, conversions, and conversion_value."
        )

    df["query"] = (
        df["query"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    numeric_columns = [
        "impressions",
        "clicks",
        "cost",
        "conversions",
        "conversion_value",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        if df[column].isna().any():
            raise ValueError(
                f"Column '{column}' contains missing or invalid "
                "numeric values. Please correct the CSV and upload it again."
            )

    if (df[numeric_columns] < 0).any().any():
        raise ValueError(
            "Metric columns cannot contain negative values."
        )

    # Impossible click-to-impression counts indicate bad input.
    if (df["clicks"] > df["impressions"]).any():
        raise ValueError(
            "Some rows have more clicks than impressions. "
            "Please check the dataset."
        )

    # Keep the original row order and remove blank search terms.
    df = df.loc[df["query"] != ""].copy()

    if df.empty:
        raise ValueError(
            "No valid search terms were found in the uploaded CSV."
        )

    return df


# ==================================================
# 5. UNCERTAINTY-AWARE TRIAGE ENGINE
# ==================================================

def triage(row: pd.Series) -> dict:
    """
    Apply transparent, conservative classification rules.

    Confidence is a heuristic score, not a statistically
    calibrated probability.
    """

    clicks = float(row["clicks"])
    impressions = float(row["impressions"])
    cost = float(row["cost"])
    conversions = float(row["conversions"])
    conversion_value = float(row["conversion_value"])

    # --------------------------------------------------
    # RULE 1: VERY LITTLE EVIDENCE
    # --------------------------------------------------

    if clicks < 20:
        return {
            "decision": "ignore",
            "confidence": 0.35,
            "review_required": True,
            "reason": (
                "Insufficient click data to judge performance. "
                "Leave unchanged and collect more evidence."
            ),
        }

    # --------------------------------------------------
    # RULE 2: STRONGER EVIDENCE FOR PROMOTION
    # --------------------------------------------------

    if (
        clicks >= 50
        and conversions >= 3
        and conversion_value > cost
    ):
        return {
            "decision": "promote",
            "confidence": 0.78,
            "review_required": False,
            "reason": (
                "At least 50 clicks and 3 conversions, with "
                "conversion value exceeding cost. Eligible for promotion."
            ),
        }

    # --------------------------------------------------
    # RULE 3: POSITIVE SIGNAL, BUT NOT ENOUGH EVIDENCE
    # --------------------------------------------------

    if (
        conversions >= 1
        and conversion_value > cost
    ):
        return {
            "decision": "ignore",
            "confidence": 0.48,
            "review_required": True,
            "reason": (
                "Positive conversion value, but evidence does not "
                "meet the promotion threshold. Review before acting."
            ),
        }

    # --------------------------------------------------
    # RULE 4: SPEND WITHOUT CONVERSIONS
    # --------------------------------------------------

    if clicks >= 75 and conversions == 0 and cost > 0:
        return {
            "decision": "block",
            "confidence": 0.72,
            "review_required": True,
            "reason": (
                "At least 75 clicks with spend and no conversions. "
                "Consider blocking after human review."
            ),
        }

    # --------------------------------------------------
    # RULE 5: MODERATE CLICK VOLUME, NO CONVERSIONS
    # --------------------------------------------------

    if clicks >= 30 and conversions == 0 and cost > 0:
        return {
            "decision": "ignore",
            "confidence": 0.50,
            "review_required": True,
            "reason": (
                "No conversions despite moderate click volume. "
                "Evidence is not strong enough for an automatic block."
            ),
        }

    # --------------------------------------------------
    # RULE 6: ALL OTHER AMBIGUOUS CASES
    # --------------------------------------------------

    return {
        "decision": "ignore",
        "confidence": 0.40,
        "review_required": True,
        "reason": (
            "Performance signals are inconclusive. "
            "Keep unchanged and request human review."
        ),
    }


# ==================================================
# 6. ANALYZE ALL SEARCH TERMS
# ==================================================

def analyze_dataframe(df: pd.DataFrame) -> dict:
    """Return decisions, explanations, and summary metrics."""

    results = []

    # itertuples is generally faster than iterrows on large CSVs.
    for row in df.itertuples(index=False):
        record = row._asdict()

        classification = triage(
            pd.Series(record)
        )

        item = {
            "query": str(record["query"]),
            "match_type": str(record.get("match_type", "")),
            "campaign": str(record.get("campaign", "")),
            "ad_group": str(record.get("ad_group", "")),
            "impressions": int(record["impressions"]),
            "clicks": int(record["clicks"]),
            "cost": round(float(record["cost"]), 2),
            "conversions": float(record["conversions"]),
            "conversion_value": round(
                float(record["conversion_value"]), 2
            ),
            **classification,
        }

        results.append(item)

    promote_count = sum(
        item["decision"] == "promote" for item in results
    )

    block_count = sum(
        item["decision"] == "block" for item in results
    )

    ignore_count = sum(
        item["decision"] == "ignore" for item in results
    )

    review_count = sum(
        item["review_required"] for item in results
    )

    return {
        "total_terms": len(results),
        "promote": promote_count,
        "block": block_count,
        "ignore": ignore_count,
        "review_required": review_count,
        "total_clicks": sum(
            item["clicks"] for item in results
        ),
        "total_impressions": sum(
            item["impressions"] for item in results
        ),
        "total_cost": round(
            sum(item["cost"] for item in results), 2
        ),
        "total_conversions": sum(
            item["conversions"] for item in results
        ),
        "total_conversion_value": round(
            sum(item["conversion_value"] for item in results), 2
        ),
        "results": results,
    }


# ==================================================
# 7. READ AND VALIDATE UPLOADED CSV
# ==================================================

async def read_uploaded_csv(file: UploadFile) -> pd.DataFrame:
    """Read CSV content and prepare its columns."""

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a file with the .csv extension.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    try:
        try:
            df = pd.read_csv(BytesIO(content))
        except UnicodeDecodeError:
            df = pd.read_csv(
                BytesIO(content),
                encoding="latin-1",
            )

        return prepare_columns(df)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not process the CSV: {exc}",
        ) from exc


# ==================================================
# 8. HOME ENDPOINT
# ==================================================

@app.get("/")
def home():
    return {
        "message": "Search Term Triage Engine API is running.",
        "version": "2.0.0",
        "documentation": "/docs",
        "health": "/health",
    }


# ==================================================
# 9. HEALTH CHECK
# ==================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "Backend is running successfully.",
    }


# ==================================================
# 10. UPLOAD AND ANALYZE
# ==================================================

@app.post("/triage/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Analyze an uploaded search-term report."""

    df = await read_uploaded_csv(file)

    try:
        return analyze_dataframe(df)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Search-term analysis failed: {exc}",
        ) from exc


# ==================================================
# 11. EXPORT ANALYSIS RESULTS
# ==================================================

@app.post("/triage/export")
async def export_results(file: UploadFile = File(...)):
    """Return a classified CSV file for analyst review."""

    df = await read_uploaded_csv(file)

    try:
        analysis = analyze_dataframe(df)

        output_df = pd.DataFrame(analysis["results"])
        csv_content = output_df.to_csv(index=False)

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    'attachment; filename="triage_results.csv"'
                )
            },
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"CSV export failed: {exc}",
        ) from exc
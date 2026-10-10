"""FastAPI backend for QueryPilot Search Term Triage Engine.

Wraps the existing deterministic triage engine (triage/) and exposes REST
endpoints for the React frontend.
"""

from __future__ import annotations

import io
import json
import traceback
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from triage.config import ColumnMapping, TriageConfig
from triage.engine import run_triage_engine
from triage.export import filter_and_sort_results, results_to_csv_string
from triage.loader import load_csv_flexible, suggest_column_mapping

app = FastAPI(
    title="QueryPilot API",
    description="Search Term Triage Engine — Statistical Analysis Backend",
    version="1.0.0",
)

# Restrict CORS to development and Vercel preview environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB max upload limit


async def _read_and_decode_upload(file: UploadFile) -> str:
    """Safely read uploaded CSV with file-size limits and encoding fallback."""
    content = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Uploaded file exceeds the maximum allowed limit of 25 MB.",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded CSV file is empty.",
        )
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return content.decode("latin-1")
        except Exception as err:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to decode CSV file with UTF-8 or Latin-1: {err}",
            )


class NumpyEncoder(json.JSONEncoder):
    """Handle NumPy types in JSON serialization."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            if np.isnan(obj):
                return None
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return super().default(obj)


def _clean_for_json(obj: Any) -> Any:
    """Recursively clean NaN/Inf values for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_for_json(v) for v in obj]
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


@app.get("/api/health")
@app.get("/health")
async def health_check():
    return {"status": "ok", "engine": "QueryPilot Triage Engine v1.0"}


@app.post("/api/preview")
@app.post("/preview")
async def preview_csv(file: UploadFile = File(...)):
    """Preview CSV headers and suggest column mappings."""
    try:
        text = await _read_and_decode_upload(file)
        df = load_csv_flexible(io.StringIO(text))

        columns = list(df.columns)
        suggested = suggest_column_mapping(columns)
        sample_rows = df.head(5).fillna("").to_dict(orient="records")

        return JSONResponse(content={
            "columns": columns,
            "suggested_mapping": suggested,
            "sample_rows": sample_rows,
            "total_rows": len(df),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")


@app.post("/api/analyze")
@app.post("/analyze")
async def analyze_csv(
    file: UploadFile = File(...),
    column_mapping: str = Form(...),
    config: Optional[str] = Form(None),
):
    """Run the full triage analysis on uploaded CSV data.

    Args:
        file: CSV file upload
        column_mapping: JSON string of column mapping
        config: Optional JSON string of TriageConfig overrides
    """
    try:
        # Parse inputs
        text = await _read_and_decode_upload(file)
        df = load_csv_flexible(io.StringIO(text))

        mapping_dict = json.loads(column_mapping)
        mapping = ColumnMapping(
            search_term=mapping_dict["search_term"],
            clicks=mapping_dict["clicks"],
            cost=mapping_dict["cost"],
            conversions=mapping_dict["conversions"],
            campaign=mapping_dict.get("campaign"),
            ad_group=mapping_dict.get("ad_group"),
            match_type=mapping_dict.get("match_type"),
            impressions=mapping_dict.get("impressions"),
            conversion_value=mapping_dict.get("conversion_value"),
        )

        cfg = TriageConfig()
        if config:
            config_dict = json.loads(config)
            cfg = TriageConfig(
                alpha=config_dict.get("alpha", 0.05),
                shrinkage_k=config_dict.get("shrinkage_k", 100.0),
                min_test_clicks=config_dict.get("min_test_clicks", 10),
                min_promote_conversions=config_dict.get("min_promote_conversions", 2.0),
                block_cost_cpa_multiplier=config_dict.get("block_cost_cpa_multiplier", 1.0),
                fallback_block_cost_floor=config_dict.get("fallback_block_cost_floor", 25.0),
                strict_fdr_gate=config_dict.get("strict_fdr_gate", False),
            )

        # Run the engine
        result_df, summary, quality_report = run_triage_engine(df, mapping, cfg)

        # Convert results to JSON-safe dicts
        results_records = result_df.to_dict(orient="records")
        results_clean = _clean_for_json(results_records)
        summary_clean = _clean_for_json(summary.to_dict())
        quality_clean = _clean_for_json(quality_report.to_dict())

        # Compute decision distribution
        decision_counts = result_df["decision"].value_counts().to_dict()

        # Compute campaign summary
        campaign_summary = (
            result_df.groupby("campaign")
            .agg(
                total=("decision", "count"),
                promote=("decision", lambda x: (x == "PROMOTE").sum()),
                block=("decision", lambda x: (x == "BLOCK").sum()),
                ignore=("decision", lambda x: (x == "IGNORE").sum()),
                total_cost=("cost", "sum"),
                total_clicks=("clicks", "sum"),
                total_conversions=("conversions", "sum"),
            )
            .reset_index()
            .to_dict(orient="records")
        )

        return JSONResponse(content={
            "results": results_clean,
            "summary": summary_clean,
            "quality_report": quality_clean,
            "decision_counts": _clean_for_json(decision_counts),
            "campaign_summary": _clean_for_json(campaign_summary),
        })

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal analysis error during statistical execution.")


@app.post("/api/export")
@app.post("/export")
async def export_csv(
    results: str = Form(...),
    filters: Optional[str] = Form(None),
):
    """Export filtered results as downloadable CSV."""
    try:
        results_list = json.loads(results)
        result_df = pd.DataFrame(results_list)

        if filters:
            filter_dict = json.loads(filters)
            result_df = filter_and_sort_results(
                result_df,
                decisions=filter_dict.get("decisions"),
                campaigns=filter_dict.get("campaigns"),
                match_types=filter_dict.get("match_types"),
                review_only=filter_dict.get("review_only", False),
                search_query=filter_dict.get("search_query", ""),
                sort_by=filter_dict.get("sort_by", "row_id"),
                ascending=filter_dict.get("ascending", True),
            )

        csv_string = results_to_csv_string(result_df)

        return StreamingResponse(
            io.BytesIO(csv_string.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=querypilot_triage_results.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

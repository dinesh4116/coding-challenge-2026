import os
import io
import re
import math
import uuid
import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd

from database import init_db, get_db_connection
from triage_engine import triage_search_terms, generate_negative_keyword_suggestions
from demo_data import generate_realistic_dataset, generate_stress_test_dataset
from csv_loader import load_search_terms_csv, standardize_dataframe, CsvLoadError

# Initialize database schema
init_db()

app = FastAPI(
    title="SearchPilot AI Backend",
    description="Intelligent Google Ads Search Term Triage Engine API",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = (".csv", ".tsv", ".txt")


def map_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise any Google Ads style DataFrame (demo data, stress test) to the internal schema."""
    cleaned, _info = standardize_dataframe(df)
    return cleaned


def _safe_dataset_id(dataset_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,64}", dataset_id or ""):
        raise HTTPException(status_code=400, detail="Invalid dataset id.")
    return dataset_id


def _dataset_frame_path(dataset_id: str) -> str:
    return os.path.join(UPLOAD_DIR, f"{_safe_dataset_id(dataset_id)}.csv")


# Pydantic Schemas
class ReviewRequest(BaseModel):
    term_id: int
    action: str  # 'PROMOTE', 'BLOCK', 'IGNORE'
    reviewer_notes: Optional[str] = ""

class BatchReviewRequest(BaseModel):
    term_ids: List[int]
    action: str
    reviewer_notes: Optional[str] = ""

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "SearchPilot AI Triage Engine",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

PROJECT_ZIP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "searchpilot-ai-full-project.zip")

@app.get("/api/download-zip")
def download_project_zip():
    if not os.path.exists(PROJECT_ZIP_PATH):
        internal_zip = os.path.join(os.path.dirname(os.path.abspath(__file__)), "searchpilot-ai-full-project.zip")
        if os.path.exists(internal_zip):
            return FileResponse(internal_zip, media_type="application/zip", filename="searchpilot-ai-full-project.zip")
        raise HTTPException(status_code=404, detail="Project zip file not found")
    return FileResponse(
        PROJECT_ZIP_PATH,
        media_type="application/zip",
        filename="searchpilot-ai-full-project.zip"
    )



@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Upload and validate a Google Ads search term CSV. Supports 25k+ rows."""
    filename = file.filename or "upload.csv"
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Uploaded file must be a CSV (.csv) export.")

    contents = await file.read()
    try:
        mapped_df, info = load_search_terms_csv(contents)
    except CsvLoadError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV file: {exc}")

    dataset_id = str(uuid.uuid4())[:8]
    row_count = len(mapped_df)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Keep the cleaned data on the server so analysis never needs the file re-sent.
    mapped_df.to_csv(_dataset_frame_path(dataset_id), index=False)

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO datasets (id, name, filename, row_count, created_at, status) VALUES (?, ?, ?, ?, ?, ?)",
            (dataset_id, filename, filename, row_count, now_iso, "uploaded"),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "success": True,
        "dataset_id": dataset_id,
        "filename": filename,
        "row_count": row_count,
        "original_columns": info["original_columns"],
        "mapped_columns": info["mapped_columns"],
        "skipped_rows": info["skipped_rows"],
        "warnings": info["warnings"],
        "encoding": info["encoding"],
        "delimiter": info["delimiter"],
        "preview": mapped_df.head(10).to_dict(orient="records"),
    }

@app.post("/api/analyze")
async def analyze_dataset(
    dataset_id: str = Form(...),
    target_cpa: float = Form(35.0),
    target_roas: float = Form(3.0),
    file: Optional[UploadFile] = File(None)
):
    """Run full statistical and NLP triage pipeline on an uploaded dataset."""
    _safe_dataset_id(dataset_id)

    if file is not None and file.filename:
        # Optional: analyse a freshly supplied file instead of the stored upload
        try:
            mapped_df, _info = load_search_terms_csv(await file.read())
        except CsvLoadError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        mapped_df.to_csv(_dataset_frame_path(dataset_id), index=False)
    else:
        frame_path = _dataset_frame_path(dataset_id)
        if not os.path.isfile(frame_path):
            raise HTTPException(status_code=400, detail="Uploaded data was not found. Please upload the CSV again.")
        mapped_df = pd.read_csv(frame_path, keep_default_na=False)
        mapped_df, _info = standardize_dataframe(mapped_df)

    conn = get_db_connection()
    cursor = conn.cursor()
    if cursor.execute("SELECT 1 FROM datasets WHERE id = ?", (dataset_id,)).fetchone() is None:
        cursor.execute(
            "INSERT INTO datasets (id, name, filename, row_count, created_at, status) VALUES (?, ?, ?, ?, ?, ?)",
            (dataset_id, getattr(file, "filename", None) or dataset_id, getattr(file, "filename", None) or dataset_id,
             len(mapped_df), datetime.datetime.now(datetime.timezone.utc).isoformat(), "uploaded"),
        )

    # Execute Triage Engine
    try:
        processed_df = triage_search_terms(mapped_df, target_cpa=target_cpa, target_roas=target_roas)
    except Exception as exc:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    # Insert into database in batch
    cursor.execute("DELETE FROM search_terms WHERE dataset_id = ?", (dataset_id,))
    cursor.execute("DELETE FROM negative_keywords WHERE dataset_id = ?", (dataset_id,))

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    insert_records = []
    for _, row in processed_df.iterrows():
        insert_records.append((
            dataset_id,
            str(row["query"]),
            str(row["campaign"]),
            str(row["ad_group"]),
            str(row["match_type"]),
            int(row["impressions"]),
            int(row["clicks"]),
            float(row["cost"]),
            float(row["conversions"]),
            float(row["conversion_value"]),
            float(row["ctr"]),
            float(row["cvr"]),
            float(row["cpa"]),
            float(row["roas"]),
            float(row["cpc"]),
            str(row["action"]),
            float(row["confidence"]),
            str(row["reason"]),
            str(row["missing_info"]),
            str(row["financial_impact"]),
            int(row["needs_review"]),
            "PENDING",
            None,
            "",
            now_iso
        ))

    cursor.executemany("""
        INSERT INTO search_terms (
            dataset_id, query, campaign, ad_group, match_type, impressions, clicks,
            cost, conversions, conversion_value, ctr, cvr, cpa, roas, cpc, action,
            confidence, reason, missing_info, financial_impact, needs_review,
            review_status, reviewer_action, reviewer_notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insert_records)

    # Update dataset status and count
    cursor.execute("UPDATE datasets SET status = 'analyzed', row_count = ? WHERE id = ?", (len(insert_records), dataset_id))

    # Generate Negative Keyword suggestions for BLOCK items
    cursor.execute("SELECT id, query, campaign, ad_group, cost, reason FROM search_terms WHERE dataset_id = ? AND action = 'BLOCK'", (dataset_id,))
    block_rows = cursor.fetchall()
    
    if block_rows:
        block_df = pd.DataFrame([dict(r) for r in block_rows])
        all_terms_df = processed_df[["query", "conversions"]].copy()
        neg_suggestions = generate_negative_keyword_suggestions(block_df, all_terms_df)
        
        neg_records = []
        for neg in neg_suggestions:
            neg_records.append((
                neg["term_id"],
                dataset_id,
                neg["keyword"],
                neg["match_type"],
                neg["scope"],
                neg["campaign"],
                neg["ad_group"],
                neg["reason"],
                neg["estimated_waste"],
                "PENDING"
            ))

        cursor.executemany("""
            INSERT INTO negative_keywords (
                term_id, dataset_id, keyword, match_type, scope, campaign, ad_group,
                reason, estimated_waste, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, neg_records)

    conn.commit()
    conn.close()

    return {
        "success": True,
        "dataset_id": dataset_id,
        "total_analyzed": len(processed_df),
        "promote_count": int((processed_df["action"] == "PROMOTE").sum()),
        "block_count": int((processed_df["action"] == "BLOCK").sum()),
        "ignore_count": int((processed_df["action"] == "IGNORE").sum()),
        "needs_review_count": int((processed_df["needs_review"] == 1).sum()),
    }

@app.post("/api/load-demo")
def load_sample_data():
    """One-click sample dataset setup."""
    demo_df = generate_realistic_dataset(n_target_rows=650)
    mapped_df = map_dataframe_columns(demo_df)
    processed_df = triage_search_terms(mapped_df, target_cpa=35.0, target_roas=3.0)

    dataset_id = "sample-q4-ads"
    dataset_name = "Q4 Omnichannel Search Terms"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
    cursor.execute("DELETE FROM search_terms WHERE dataset_id = ?", (dataset_id,))
    cursor.execute("DELETE FROM negative_keywords WHERE dataset_id = ?", (dataset_id,))
    cursor.execute("DELETE FROM audit_logs")

    cursor.execute(
        "INSERT INTO datasets (id, name, filename, row_count, created_at, status) VALUES (?, ?, ?, ?, ?, ?)",
        (dataset_id, dataset_name, "google_ads_sample_export.csv", len(processed_df), now_iso, "analyzed")
    )

    insert_records = []
    for _, row in processed_df.iterrows():
        insert_records.append((
            dataset_id,
            str(row["query"]),
            str(row["campaign"]),
            str(row["ad_group"]),
            str(row["match_type"]),
            int(row["impressions"]),
            int(row["clicks"]),
            float(row["cost"]),
            float(row["conversions"]),
            float(row["conversion_value"]),
            float(row["ctr"]),
            float(row["cvr"]),
            float(row["cpa"]),
            float(row["roas"]),
            float(row["cpc"]),
            str(row["action"]),
            float(row["confidence"]),
            str(row["reason"]),
            str(row["missing_info"]),
            str(row["financial_impact"]),
            int(row["needs_review"]),
            "PENDING",
            None,
            "",
            now_iso
        ))

    cursor.executemany("""
        INSERT INTO search_terms (
            dataset_id, query, campaign, ad_group, match_type, impressions, clicks,
            cost, conversions, conversion_value, ctr, cvr, cpa, roas, cpc, action,
            confidence, reason, missing_info, financial_impact, needs_review,
            review_status, reviewer_action, reviewer_notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insert_records)

    # Populate negative keywords
    cursor.execute("SELECT id, query, campaign, ad_group, cost, reason FROM search_terms WHERE dataset_id = ? AND action = 'BLOCK'", (dataset_id,))
    block_rows = cursor.fetchall()
    if block_rows:
        block_df = pd.DataFrame([dict(r) for r in block_rows])
        all_terms_df = processed_df[["query", "conversions"]].copy()
        neg_suggestions = generate_negative_keyword_suggestions(block_df, all_terms_df)
        
        neg_records = []
        for neg in neg_suggestions:
            neg_records.append((
                neg["term_id"],
                dataset_id,
                neg["keyword"],
                neg["match_type"],
                neg["scope"],
                neg["campaign"],
                neg["ad_group"],
                neg["reason"],
                neg["estimated_waste"],
                "PENDING"
            ))

        cursor.executemany("""
            INSERT INTO negative_keywords (
                term_id, dataset_id, keyword, match_type, scope, campaign, ad_group,
                reason, estimated_waste, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, neg_records)

    conn.commit()
    conn.close()

    return {
        "success": True,
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "row_count": len(processed_df),
        "message": "Sample dataset loaded and analyzed successfully!"
    }

@app.post("/api/stress-test")
def run_stress_test_25k():
    """Generates and triages 25,000 rows to demonstrate sub-second statistical execution."""
    start_time = datetime.datetime.now()
    large_df = generate_stress_test_dataset(n_rows=25000)
    mapped_df = map_dataframe_columns(large_df)
    processed_df = triage_search_terms(mapped_df)
    elapsed = (datetime.datetime.now() - start_time).total_seconds()

    return {
        "success": True,
        "rows_processed": len(processed_df),
        "execution_time_seconds": round(elapsed, 2),
        "throughput_rows_per_second": round(len(processed_df) / max(0.01, elapsed), 0),
        "promote_count": int((processed_df["action"] == "PROMOTE").sum()),
        "block_count": int((processed_df["action"] == "BLOCK").sum()),
        "ignore_count": int((processed_df["action"] == "IGNORE").sum())
    }

@app.get("/api/summary")
def get_summary(dataset_id: Optional[str] = Query(None)):
    """Retrieve computed dashboard statistics calculated strictly from the dataset."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if not dataset_id:
        cursor.execute("SELECT id FROM datasets ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"has_data": False}
        dataset_id = row["id"]

    # Total counts and sums
    cursor.execute("""
        SELECT 
            COUNT(*) as total_terms,
            SUM(CASE WHEN action = 'PROMOTE' THEN 1 ELSE 0 END) as promote_count,
            SUM(CASE WHEN action = 'BLOCK' THEN 1 ELSE 0 END) as block_count,
            SUM(CASE WHEN action = 'IGNORE' THEN 1 ELSE 0 END) as ignore_count,
            SUM(CASE WHEN needs_review = 1 THEN 1 ELSE 0 END) as review_needed_count,
            SUM(CASE WHEN review_status != 'PENDING' THEN 1 ELSE 0 END) as reviewed_count,
            SUM(CASE WHEN action = 'BLOCK' THEN cost ELSE 0 END) as estimated_waste_saved,
            SUM(impressions) as total_impressions,
            SUM(clicks) as total_clicks,
            SUM(cost) as total_spend,
            SUM(conversions) as total_conversions,
            SUM(conversion_value) as total_conversion_value,
            AVG(confidence) as avg_confidence
        FROM search_terms
        WHERE dataset_id = ?
    """, (dataset_id,))
    summary_stats = dict(cursor.fetchone())

    # Confidence distribution
    cursor.execute("""
        SELECT
            SUM(CASE WHEN confidence >= 80 THEN 1 ELSE 0 END) as high_conf,
            SUM(CASE WHEN confidence >= 60 AND confidence < 80 THEN 1 ELSE 0 END) as med_conf,
            SUM(CASE WHEN confidence < 60 THEN 1 ELSE 0 END) as low_conf
        FROM search_terms
        WHERE dataset_id = ?
    """, (dataset_id,))
    conf_dist = dict(cursor.fetchone())

    # Campaign breakdown
    cursor.execute("""
        SELECT 
            campaign,
            COUNT(*) as total,
            SUM(CASE WHEN action = 'PROMOTE' THEN 1 ELSE 0 END) as promote,
            SUM(CASE WHEN action = 'BLOCK' THEN 1 ELSE 0 END) as block,
            SUM(CASE WHEN action = 'IGNORE' THEN 1 ELSE 0 END) as ignore,
            ROUND(SUM(cost), 2) as spend,
            ROUND(SUM(conversion_value), 2) as conversion_value
        FROM search_terms
        WHERE dataset_id = ?
        GROUP BY campaign
        ORDER BY total DESC
    """, (dataset_id,))
    campaign_breakdown = [dict(r) for r in cursor.fetchall()]

    # Spend vs Conversion distribution bucketed
    cursor.execute("""
        SELECT action, ROUND(SUM(cost), 2) as spend, ROUND(SUM(conversion_value), 2) as conv_value
        FROM search_terms
        WHERE dataset_id = ?
        GROUP BY action
    """, (dataset_id,))
    action_economics = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "has_data": True,
        "dataset_id": dataset_id,
        "kpis": {
            "total_terms": summary_stats["total_terms"] or 0,
            "promote_count": summary_stats["promote_count"] or 0,
            "block_count": summary_stats["block_count"] or 0,
            "ignore_count": summary_stats["ignore_count"] or 0,
            "review_needed_count": summary_stats["review_needed_count"] or 0,
            "reviewed_count": summary_stats["reviewed_count"] or 0,
            "estimated_waste_saved": round(summary_stats["estimated_waste_saved"] or 0.0, 2),
            "total_impressions": summary_stats["total_impressions"] or 0,
            "total_clicks": summary_stats["total_clicks"] or 0,
            "total_spend": round(summary_stats["total_spend"] or 0.0, 2),
            "total_conversions": round(summary_stats["total_conversions"] or 0.0, 1),
            "total_conversion_value": round(summary_stats["total_conversion_value"] or 0.0, 2),
            "avg_confidence": round(summary_stats["avg_confidence"] or 0.0, 1),
            "overall_roas": round((summary_stats["total_conversion_value"] or 0) / max(1.0, summary_stats["total_spend"] or 1.0), 2)
        },
        "confidence_distribution": conf_dist,
        "campaign_breakdown": campaign_breakdown,
        "action_economics": action_economics
    }

@app.get("/api/results")
def get_results(
    dataset_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    action: Optional[str] = Query("ALL"),
    campaign: Optional[str] = Query(None),
    needs_review: Optional[bool] = Query(None),
    confidence_band: Optional[str] = Query("ALL"), # 'HIGH', 'MEDIUM', 'LOW'
    sort_by: Optional[str] = Query("clicks"),
    sort_dir: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=200)
):
    """Retrieve paginated, filtered, sorted search terms."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if not dataset_id:
        cursor.execute("SELECT id FROM datasets ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        dataset_id = row["id"]

    where_clauses = ["dataset_id = ?"]
    params: List[Any] = [dataset_id]

    if action and action.upper() != "ALL":
        where_clauses.append("action = ?")
        params.append(action.upper())

    if search and search.strip():
        where_clauses.append("(query LIKE ? OR campaign LIKE ? OR ad_group LIKE ?)")
        search_pattern = f"%{search.strip()}%"
        params.extend([search_pattern, search_pattern, search_pattern])

    if campaign and campaign.strip() and campaign.upper() != "ALL":
        where_clauses.append("campaign = ?")
        params.append(campaign.strip())

    if needs_review is True:
        where_clauses.append("needs_review = 1")
    elif needs_review is False:
        where_clauses.append("needs_review = 0")

    if confidence_band == "HIGH":
        where_clauses.append("confidence >= 80")
    elif confidence_band == "MEDIUM":
        where_clauses.append("confidence >= 60 AND confidence < 80")
    elif confidence_band == "LOW":
        where_clauses.append("confidence < 60")

    where_sql = " WHERE " + " AND ".join(where_clauses)

    # Count total matching rows
    cursor.execute(f"SELECT COUNT(*) FROM search_terms {where_sql}", params)
    total_count = cursor.fetchone()[0]

    # Validate sort column
    valid_sort_cols = {
        "id", "query", "campaign", "ad_group", "match_type", "impressions",
        "clicks", "cost", "conversions", "conversion_value", "ctr", "cvr",
        "cpa", "roas", "action", "confidence", "needs_review", "review_status"
    }
    col = sort_by.lower() if sort_by.lower() in valid_sort_cols else "clicks"
    direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

    offset = (page - 1) * page_size
    query_sql = f"""
        SELECT * FROM search_terms
        {where_sql}
        ORDER BY {col} {direction}
        LIMIT ? OFFSET ?
    """
    cursor.execute(query_sql, params + [page_size, offset])
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "items": rows,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total_count / page_size) if page_size > 0 else 1
    }

@app.get("/api/results/{term_id}")
def get_single_term(term_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM search_terms WHERE id = ?", (term_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Search term not found")
    return dict(row)

@app.post("/api/review")
def review_search_term(req: ReviewRequest):
    """Reviewer approves, changes action, or adds notes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM search_terms WHERE id = ?", (req.term_id,))
    term = cursor.fetchone()
    if not term:
        conn.close()
        raise HTTPException(status_code=404, detail="Search term not found")

    old_action = term["action"]
    new_action = req.action.upper()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cursor.execute("""
        UPDATE search_terms
        SET action = ?,
            reviewer_action = ?,
            review_status = 'APPROVED',
            reviewer_notes = ?,
            needs_review = 0,
            updated_at = ?
        WHERE id = ?
    """, (new_action, new_action, req.reviewer_notes or "", now_iso, req.term_id))

    # Log to audit trail
    cursor.execute("""
        INSERT INTO audit_logs (term_id, query, old_action, new_action, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (req.term_id, term["query"], old_action, new_action, req.reviewer_notes or "", now_iso))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "term_id": req.term_id,
        "old_action": old_action,
        "new_action": new_action,
        "status": "APPROVED"
    }

@app.post("/api/batch-review")
def batch_review(req: BatchReviewRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for tid in req.term_ids:
        cursor.execute("SELECT action, query FROM search_terms WHERE id = ?", (tid,))
        term = cursor.fetchone()
        if term:
            cursor.execute("""
                UPDATE search_terms
                SET action = ?,
                    reviewer_action = ?,
                    review_status = 'APPROVED',
                    reviewer_notes = ?,
                    needs_review = 0,
                    updated_at = ?
                WHERE id = ?
            """, (req.action.upper(), req.action.upper(), req.reviewer_notes or "Bulk action approved", now_iso, tid))

            cursor.execute("""
                INSERT INTO audit_logs (term_id, query, old_action, new_action, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tid, term["query"], term["action"], req.action.upper(), req.reviewer_notes or "Bulk action approved", now_iso))

    conn.commit()
    conn.close()
    return {"success": True, "count": len(req.term_ids)}

@app.get("/api/negative-keywords")
def get_negative_keywords(dataset_id: Optional[str] = Query(None)):
    """Retrieve block candidates formatted as Google Ads negative keywords."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if not dataset_id:
        cursor.execute("SELECT id FROM datasets ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"items": [], "total_estimated_waste": 0.0}
        dataset_id = row["id"]

    cursor.execute("""
        SELECT * FROM negative_keywords
        WHERE dataset_id = ?
        ORDER BY estimated_waste DESC
    """, (dataset_id,))
    rows = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT SUM(estimated_waste) FROM negative_keywords WHERE dataset_id = ?", (dataset_id,))
    total_waste = cursor.fetchone()[0] or 0.0

    conn.close()
    return {
        "items": rows,
        "total_count": len(rows),
        "total_estimated_waste": round(total_waste, 2)
    }

@app.get("/api/audit-logs")
def get_audit_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 50")
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"logs": logs}

@app.get("/api/export/csv")
def export_enriched_csv(dataset_id: Optional[str] = Query(None)):
    """Download full enriched analysis CSV containing original metrics + explainable triage."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if not dataset_id:
        cursor.execute("SELECT id FROM datasets ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="No dataset found to export")
        dataset_id = row["id"]

    query = """
        SELECT 
            query as "Search Term",
            campaign as "Campaign",
            ad_group as "Ad Group",
            match_type as "Match Type",
            impressions as "Impressions",
            clicks as "Clicks",
            cost as "Cost ($)",
            conversions as "Conversions",
            conversion_value as "Conversion Value ($)",
            ctr as "CTR (%)",
            cvr as "CVR (%)",
            cpa as "CPA ($)",
            roas as "ROAS",
            action as "Recommended Action",
            confidence as "Confidence Score (%)",
            reason as "Reasoning",
            missing_info as "Missing Data Needed",
            financial_impact as "Financial Impact",
            needs_review as "Needs Review (1/0)",
            review_status as "Review Status",
            reviewer_notes as "Reviewer Notes"
        FROM search_terms
        WHERE dataset_id = ?
        ORDER BY clicks DESC
    """
    df = pd.read_sql_query(query, conn, params=[dataset_id])
    conn.close()

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=searchpilot_triage_results_{dataset_id}.csv"}
    )

@app.get("/api/export/google-ads-negatives")
def export_google_ads_negatives(dataset_id: Optional[str] = Query(None)):
    """Export formatted CSV specifically for Google Ads Editor / Bulk negative uploads."""
    conn = get_db_connection()
    if not dataset_id:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM datasets ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="No negative keywords to export")
        dataset_id = row["id"]

    query = """
        SELECT 
            keyword as "Criterion",
            match_type as "Match Type",
            campaign as "Campaign",
            ad_group as "Ad Group",
            estimated_waste as "Historical Cost ($)",
            reason as "Negative Reason"
        FROM negative_keywords
        WHERE dataset_id = ?
        ORDER BY estimated_waste DESC
    """
    df = pd.read_sql_query(query, conn, params=[dataset_id])
    conn.close()

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=google_ads_negative_keywords_{dataset_id}.csv"}
    )


# ---------------------------------------------------------------------------
# Single-host mode: serve the built React app from this same server.
# Open http://localhost:8000 - the web app and the API share one address.
# Registered LAST so every /api/... route above takes priority.
# ---------------------------------------------------------------------------
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
FRONTEND_INDEX = os.path.join(FRONTEND_DIST, "index.html")

if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    if os.path.isfile(FRONTEND_INDEX):
        candidate = os.path.normpath(os.path.join(FRONTEND_DIST, full_path))
        if full_path and candidate.startswith(FRONTEND_DIST) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_INDEX)
    return HTMLResponse(
        "<h2>SearchPilot AI</h2><p>The web app has not been built yet. "
        "Run <b>setup_and_run.bat</b> (or <code>npm run build</code> inside the frontend folder), then refresh.</p>",
        status_code=200,
    )

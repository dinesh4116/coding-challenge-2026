"""
AdCreative Intelligence - Persistent SQLite Database Layer
Manages projects, creative assets, performance datasets, statistical analyses,
creative briefs, analytical reports, and application preferences.
"""

import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "adcreative_intelligence.db"
STORAGE_DIR = BASE_DIR / "project_storage"
STORAGE_DIR.mkdir(exist_ok=True)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = str(db_path) if db_path is not None else str(DEFAULT_DB_PATH)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initializes SQLite tables for projects, assets, datasets, analyses, reports, and preferences."""
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                campaign_objective TEXT DEFAULT 'Direct Response & Conversion Optimization',
                is_synthetic INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assets (
                asset_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                ad_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                image_hash TEXT DEFAULT '',
                image_path TEXT DEFAULT '',
                width INTEGER DEFAULT 0,
                height INTEGER DEFAULT 0,
                aspect_ratio REAL DEFAULT 1.0,
                features_json TEXT DEFAULT '{}',
                extraction_status TEXT DEFAULT 'success',
                extraction_error TEXT DEFAULT '',
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                row_count INTEGER DEFAULT 0,
                matched_count INTEGER DEFAULT 0,
                unmatched_records_json TEXT DEFAULT '[]',
                unmatched_images_json TEXT DEFAULT '[]',
                excluded_records_json TEXT DEFAULT '[]',
                warnings_json TEXT DEFAULT '[]',
                errors_json TEXT DEFAULT '[]',
                records_json TEXT DEFAULT '[]',
                available_optional_cols_json TEXT DEFAULT '[]',
                is_synthetic INTEGER DEFAULT 0,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS analyses (
                analysis_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                dataset_id TEXT DEFAULT '',
                findings_json TEXT DEFAULT '[]',
                confounding_report_json TEXT DEFAULT '[]',
                summary_metrics_json TEXT DEFAULT '{}',
                total_creatives INTEGER DEFAULT 0,
                supported_count INTEGER DEFAULT 0,
                preliminary_count INTEGER DEFAULT 0,
                is_synthetic INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                analysis_id TEXT DEFAULT '',
                title TEXT NOT NULL,
                report_type TEXT NOT NULL,
                content_markdown TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                is_synthetic INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS preferences (
                pref_key TEXT PRIMARY KEY,
                pref_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def create_project(
    name: str,
    description: str = "",
    campaign_objective: str = "Direct Response & Conversion Optimization",
    is_synthetic: bool = False,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Creates a new project and returns its metadata dictionary."""
    init_db(db_path)
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Project name cannot be empty.")

    project_id = f"proj_{uuid.uuid4().hex[:10]}"
    now = _utc_now_iso()

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO projects (project_id, name, description, campaign_objective, is_synthetic, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, clean_name, description.strip(), campaign_objective.strip(), int(is_synthetic), now, now),
        )
        conn.commit()

    proj_dir = STORAGE_DIR / project_id / "images"
    proj_dir.mkdir(parents=True, exist_ok=True)

    return {
        "project_id": project_id,
        "name": clean_name,
        "description": description.strip(),
        "campaign_objective": campaign_objective.strip(),
        "is_synthetic": bool(is_synthetic),
        "created_at": now,
        "updated_at": now,
    }


def list_projects(include_synthetic: bool = True, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Lists all projects with asset, dataset, analysis, and report counts."""
    init_db(db_path)
    query = """
        SELECT
            p.*,
            (SELECT COUNT(*) FROM assets a WHERE a.project_id = p.project_id) AS asset_count,
            (SELECT COUNT(*) FROM datasets d WHERE d.project_id = p.project_id) AS dataset_count,
            (SELECT COUNT(*) FROM analyses an WHERE an.project_id = p.project_id) AS analysis_count,
            (SELECT COUNT(*) FROM reports r WHERE r.project_id = p.project_id) AS report_count
        FROM projects p
    """
    params: Tuple[Any, ...] = ()
    if not include_synthetic:
        query += " WHERE p.is_synthetic = 0"
    query += " ORDER BY p.updated_at DESC"

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_synthetic"] = bool(d["is_synthetic"])
            result.append(d)
        return result


def get_project(project_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["is_synthetic"] = bool(d["is_synthetic"])
        return d


def update_project_timestamp(project_id: str, is_synthetic: Optional[bool] = None, db_path: Optional[Path] = None) -> None:
    now = _utc_now_iso()
    with get_connection(db_path) as conn:
        if is_synthetic is not None:
            conn.execute(
                "UPDATE projects SET updated_at = ?, is_synthetic = ? WHERE project_id = ?",
                (now, int(is_synthetic), project_id),
            )
        else:
            conn.execute("UPDATE projects SET updated_at = ? WHERE project_id = ?", (now, project_id))
        conn.commit()


def delete_project(project_id: str, db_path: Optional[Path] = None) -> bool:
    """Deletes a project and all its associated records and stored image files."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
        conn.commit()
        deleted = cur.rowcount > 0

    proj_dir = STORAGE_DIR / project_id
    if proj_dir.exists():
        shutil.rmtree(proj_dir, ignore_errors=True)
    return deleted


def save_project_assets(
    project_id: str,
    images_dict: Dict[str, Any],
    features_dict: Dict[str, Dict[str, Any]],
    replace_existing: bool = True,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Persists creative images to disk and stores asset metadata + extracted features in SQLite."""
    init_db(db_path)
    proj_img_dir = STORAGE_DIR / project_id / "images"
    proj_img_dir.mkdir(parents=True, exist_ok=True)
    now = _utc_now_iso()
    saved_assets: List[Dict[str, Any]] = []

    with get_connection(db_path) as conn:
        if replace_existing:
            conn.execute("DELETE FROM assets WHERE project_id = ?", (project_id,))

        for ad_id, img_obj in images_dict.items():
            asset_id = f"ast_{uuid.uuid4().hex[:10]}"
            feat = features_dict.get(str(ad_id), {})
            status = feat.get("extraction_status", "error" if "error" in feat else "success")
            err_msg = feat.get("extraction_error", feat.get("error", "")) or ""

            # Save image file to project storage
            safe_stem = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in str(ad_id))
            filename = f"{safe_stem}.png"
            dest_path = proj_img_dir / filename

            try:
                if isinstance(img_obj, Image.Image):
                    img_obj.save(dest_path, format="PNG")
                elif isinstance(img_obj, (str, Path)) and Path(img_obj).exists():
                    Image.open(img_obj).convert("RGB").save(dest_path, format="PNG")
                elif hasattr(img_obj, "read"):
                    if hasattr(img_obj, "seek"):
                        img_obj.seek(0)
                    Image.open(img_obj).convert("RGB").save(dest_path, format="PNG")
                    if hasattr(img_obj, "seek"):
                        img_obj.seek(0)
            except Exception as e:
                if not err_msg:
                    err_msg = str(e)
                status = "error"

            width = int(feat.get("width", 0))
            height = int(feat.get("height", 0))
            aspect_ratio = float(feat.get("aspect_ratio", 1.0))
            img_hash = str(feat.get("image_hash", ""))

            conn.execute(
                """
                INSERT INTO assets (
                    asset_id, project_id, ad_id, filename, image_hash, image_path,
                    width, height, aspect_ratio, features_json, extraction_status,
                    extraction_error, uploaded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    project_id,
                    str(ad_id),
                    filename,
                    img_hash,
                    str(dest_path),
                    width,
                    height,
                    aspect_ratio,
                    json.dumps(feat),
                    status,
                    err_msg,
                    now,
                ),
            )
            saved_assets.append(
                {
                    "asset_id": asset_id,
                    "project_id": project_id,
                    "ad_id": str(ad_id),
                    "filename": filename,
                    "image_hash": img_hash,
                    "image_path": str(dest_path),
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio,
                    "features": feat,
                    "extraction_status": status,
                    "extraction_error": err_msg,
                    "uploaded_at": now,
                }
            )
        conn.commit()

    update_project_timestamp(project_id, db_path=db_path)
    return saved_assets


def get_project_assets(project_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM assets WHERE project_id = ? ORDER BY ad_id ASC",
            (project_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["features"] = json.loads(d.get("features_json") or "{}")
            except Exception:
                d["features"] = {}
            result.append(d)
        return result


def save_project_dataset(
    project_id: str,
    name: str,
    df: pd.DataFrame,
    matched_count: int,
    unmatched_records: List[str],
    unmatched_images: List[str],
    warnings: List[str],
    errors: List[str],
    excluded_records: Optional[List[Dict[str, Any]]] = None,
    available_optional_cols: Optional[List[str]] = None,
    is_synthetic: bool = False,
    replace_existing: bool = True,
    db_path: Optional[Path] = None,
) -> str:
    """Persists an imported dataset and its validation metadata to SQLite."""
    init_db(db_path)
    dataset_id = f"ds_{uuid.uuid4().hex[:10]}"
    now = _utc_now_iso()

    # Convert NaN to None for clean JSON serialization
    clean_records = json.loads(df.to_json(orient="records"))

    with get_connection(db_path) as conn:
        if replace_existing:
            conn.execute("DELETE FROM datasets WHERE project_id = ?", (project_id,))

        conn.execute(
            """
            INSERT INTO datasets (
                dataset_id, project_id, name, row_count, matched_count,
                unmatched_records_json, unmatched_images_json, excluded_records_json,
                warnings_json, errors_json, records_json, available_optional_cols_json,
                is_synthetic, uploaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                project_id,
                name,
                len(df),
                matched_count,
                json.dumps(unmatched_records),
                json.dumps(unmatched_images),
                json.dumps(excluded_records or []),
                json.dumps(warnings),
                json.dumps(errors),
                json.dumps(clean_records),
                json.dumps(available_optional_cols or []),
                int(is_synthetic),
                now,
            ),
        )
        conn.commit()

    update_project_timestamp(project_id, is_synthetic=is_synthetic, db_path=db_path)
    return dataset_id


def get_project_datasets(project_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM datasets WHERE project_id = ? ORDER BY uploaded_at DESC",
            (project_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_synthetic"] = bool(d["is_synthetic"])
            for k in (
                "unmatched_records",
                "unmatched_images",
                "excluded_records",
                "warnings",
                "errors",
                "records",
                "available_optional_cols",
            ):
                try:
                    d[k] = json.loads(d.get(f"{k}_json") or "[]")
                except Exception:
                    d[k] = []
            result.append(d)
        return result


def save_project_analysis(
    project_id: str,
    dataset_id: str,
    findings: List[Any],
    summary_metrics: Dict[str, Any],
    confounding_report: Optional[List[Dict[str, Any]]] = None,
    is_synthetic: bool = False,
    db_path: Optional[Path] = None,
) -> str:
    """Persists statistical findings and confounding analysis for a project."""
    init_db(db_path)
    analysis_id = f"anl_{uuid.uuid4().hex[:10]}"
    now = _utc_now_iso()

    serialized_findings = [f.to_dict() if hasattr(f, "to_dict") else f for f in findings]
    supported_count = sum(
        1 for f in serialized_findings if f.get("evidence_classification") == "Supported association"
    )
    preliminary_count = sum(
        1 for f in serialized_findings if f.get("evidence_classification") in ("Preliminary", "Preliminary evidence")
    )
    total_creatives = int(summary_metrics.get("total_creatives", 0))

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO analyses (
                analysis_id, project_id, dataset_id, findings_json,
                confounding_report_json, summary_metrics_json,
                total_creatives, supported_count, preliminary_count,
                is_synthetic, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                project_id,
                dataset_id,
                json.dumps(serialized_findings),
                json.dumps(confounding_report or []),
                json.dumps(summary_metrics),
                total_creatives,
                supported_count,
                preliminary_count,
                int(is_synthetic),
                now,
            ),
        )
        conn.commit()

    update_project_timestamp(project_id, db_path=db_path)
    return analysis_id


def get_project_analyses(project_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM analyses WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_synthetic"] = bool(d["is_synthetic"])
            try:
                d["findings"] = json.loads(d.get("findings_json") or "[]")
            except Exception:
                d["findings"] = []
            try:
                d["confounding_report"] = json.loads(d.get("confounding_report_json") or "[]")
            except Exception:
                d["confounding_report"] = []
            try:
                d["summary_metrics"] = json.loads(d.get("summary_metrics_json") or "{}")
            except Exception:
                d["summary_metrics"] = {}
            result.append(d)
        return result


def save_project_report(
    project_id: str,
    analysis_id: str,
    title: str,
    report_type: str,
    content_markdown: str,
    metadata: Optional[Dict[str, Any]] = None,
    is_synthetic: bool = False,
    db_path: Optional[Path] = None,
) -> str:
    init_db(db_path)
    report_id = f"rep_{uuid.uuid4().hex[:10]}"
    now = _utc_now_iso()
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO reports (
                report_id, project_id, analysis_id, title, report_type,
                content_markdown, metadata_json, is_synthetic, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                project_id,
                analysis_id,
                title,
                report_type,
                content_markdown,
                json.dumps(metadata or {}),
                int(is_synthetic),
                now,
            ),
        )
        conn.commit()
    update_project_timestamp(project_id, db_path=db_path)
    return report_id


def get_project_reports(project_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM reports WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_synthetic"] = bool(d["is_synthetic"])
            try:
                d["metadata"] = json.loads(d.get("metadata_json") or "{}")
            except Exception:
                d["metadata"] = {}
            result.append(d)
        return result


def get_workspace_summary(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Computes live workspace-wide metrics and recent activity strictly from database state."""
    init_db(db_path)
    projects = list_projects(include_synthetic=True, db_path=db_path)

    with get_connection(db_path) as conn:
        total_assets = int(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0])
        total_datasets = int(conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0])
        total_analyses = int(conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0])
        total_reports = int(conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0])

        recent_assets_rows = conn.execute(
            """
            SELECT a.*, p.name AS project_name, p.is_synthetic
            FROM assets a
            JOIN projects p ON a.project_id = p.project_id
            ORDER BY a.uploaded_at DESC LIMIT 8
            """
        ).fetchall()

        recent_analyses_rows = conn.execute(
            """
            SELECT an.*, p.name AS project_name
            FROM analyses an
            JOIN projects p ON an.project_id = p.project_id
            ORDER BY an.created_at DESC LIMIT 5
            """
        ).fetchall()

    recent_assets = []
    for r in recent_assets_rows:
        d = dict(r)
        try:
            d["features"] = json.loads(d.get("features_json") or "{}")
        except Exception:
            d["features"] = {}
        recent_assets.append(d)

    recent_analyses = []
    recent_findings = []
    for r in recent_analyses_rows:
        d = dict(r)
        try:
            f_list = json.loads(d.get("findings_json") or "[]")
        except Exception:
            f_list = []
        d["findings"] = f_list
        recent_analyses.append(d)
        for f in f_list[:3]:
            if len(recent_findings) < 6:
                recent_findings.append({**f, "project_name": d["project_name"], "project_id": d["project_id"]})

    return {
        "total_projects": len(projects),
        "total_creatives_analyzed": total_assets,
        "total_datasets": total_datasets,
        "total_analyses": total_analyses,
        "total_reports": total_reports,
        "recent_projects": projects[:6],
        "recent_assets": recent_assets,
        "recent_analyses": recent_analyses,
        "recent_findings": recent_findings,
    }


def set_preference(key: str, value: Any, db_path: Optional[Path] = None) -> None:
    init_db(db_path)
    now = _utc_now_iso()
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO preferences (pref_key, pref_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(pref_key) DO UPDATE SET pref_value = excluded.pref_value, updated_at = excluded.updated_at
            """,
            (key, json.dumps(value), now),
        )
        conn.commit()


def get_preference(key: str, default: Any = None, db_path: Optional[Path] = None) -> Any:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT pref_value FROM preferences WHERE pref_key = ?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except Exception:
            return row[0]


def clear_all_data(synthetic_only: bool = False, db_path: Optional[Path] = None) -> int:
    """Deletes either synthetic projects only or all projects from SQLite and storage."""
    init_db(db_path)
    projects = list_projects(include_synthetic=True, db_path=db_path)
    deleted_count = 0
    for p in projects:
        if synthetic_only and not p.get("is_synthetic"):
            continue
        if delete_project(p["project_id"], db_path=db_path):
            deleted_count += 1
    return deleted_count

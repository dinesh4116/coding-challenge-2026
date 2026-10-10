import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "searchpilot.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS datasets (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        filename TEXT NOT NULL,
        row_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ready'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS search_terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_id TEXT NOT NULL,
        query TEXT NOT NULL,
        campaign TEXT NOT NULL,
        ad_group TEXT NOT NULL,
        match_type TEXT NOT NULL,
        impressions INTEGER NOT NULL DEFAULT 0,
        clicks INTEGER NOT NULL DEFAULT 0,
        cost REAL NOT NULL DEFAULT 0.0,
        conversions REAL NOT NULL DEFAULT 0.0,
        conversion_value REAL NOT NULL DEFAULT 0.0,
        ctr REAL NOT NULL DEFAULT 0.0,
        cvr REAL NOT NULL DEFAULT 0.0,
        cpa REAL NOT NULL DEFAULT 0.0,
        roas REAL NOT NULL DEFAULT 0.0,
        cpc REAL NOT NULL DEFAULT 0.0,
        action TEXT NOT NULL,
        confidence REAL NOT NULL,
        reason TEXT NOT NULL,
        missing_info TEXT,
        financial_impact TEXT,
        needs_review INTEGER NOT NULL DEFAULT 0,
        review_status TEXT NOT NULL DEFAULT 'PENDING',
        reviewer_action TEXT,
        reviewer_notes TEXT,
        updated_at TEXT,
        FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_st_dataset_id ON search_terms(dataset_id);
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_st_action ON search_terms(action);
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_st_needs_review ON search_terms(needs_review);
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS negative_keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term_id INTEGER NOT NULL,
        dataset_id TEXT NOT NULL,
        keyword TEXT NOT NULL,
        match_type TEXT NOT NULL,
        scope TEXT NOT NULL,
        campaign TEXT NOT NULL,
        ad_group TEXT NOT NULL,
        reason TEXT NOT NULL,
        estimated_waste REAL NOT NULL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'PENDING',
        FOREIGN KEY (term_id) REFERENCES search_terms(id) ON DELETE CASCADE,
        FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term_id INTEGER NOT NULL,
        query TEXT NOT NULL,
        old_action TEXT NOT NULL,
        new_action TEXT NOT NULL,
        notes TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (term_id) REFERENCES search_terms(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)

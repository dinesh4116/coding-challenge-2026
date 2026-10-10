import sqlite3
import os
import json
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'triage_engine.db')

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS review_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_id TEXT,
            search_term TEXT NOT NULL,
            campaign TEXT,
            ad_group TEXT,
            original_decision TEXT NOT NULL,
            reviewer_decision TEXT NOT NULL,
            reason TEXT,
            notes TEXT,
            timestamp TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS negative_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_id TEXT,
            search_term TEXT NOT NULL,
            suggested_negative TEXT NOT NULL,
            campaign TEXT,
            ad_group TEXT,
            match_type TEXT NOT NULL DEFAULT 'Exact',
            scope TEXT NOT NULL DEFAULT 'Campaign',
            reason TEXT,
            confidence REAL,
            status TEXT NOT NULL DEFAULT 'Pending',
            timestamp TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            dataset_name TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            promote_count INTEGER NOT NULL,
            block_count INTEGER NOT NULL,
            ignore_count INTEGER NOT NULL,
            review_count INTEGER NOT NULL,
            total_spend REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# Review Feedback Operations
def save_feedback(row_id, search_term, campaign, ad_group, original_decision, reviewer_decision, reason="", notes=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute('''
        INSERT INTO review_feedback (row_id, search_term, campaign, ad_group, original_decision, reviewer_decision, reason, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (row_id, search_term, campaign, ad_group, original_decision, reviewer_decision, reason, notes, now))
    feedback_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return feedback_id

def get_all_feedback():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM review_feedback ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_all_feedback():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM review_feedback')
    conn.commit()
    conn.close()

def delete_feedback_item(feedback_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM review_feedback WHERE id = ?', (feedback_id,))
    conn.commit()
    conn.close()

# Negative Keywords Operations
def save_negative_keywords(negatives_list):
    """
    negatives_list: list of dicts with keys:
    search_term, suggested_negative, campaign, ad_group, match_type, scope, reason, confidence, status
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    for item in negatives_list:
        cursor.execute('''
            INSERT INTO negative_keywords (row_id, search_term, suggested_negative, campaign, ad_group, match_type, scope, reason, confidence, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.get('row_id', ''),
            item['search_term'],
            item.get('suggested_negative', item['search_term']),
            item.get('campaign', ''),
            item.get('ad_group', ''),
            item.get('match_type', 'Exact'),
            item.get('scope', 'Campaign'),
            item.get('reason', ''),
            item.get('confidence', 0),
            item.get('status', 'Pending'),
            now
        ))
    conn.commit()
    conn.close()

def get_all_negative_keywords():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM negative_keywords ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_negative_keyword(neg_id, updates):
    conn = get_db_connection()
    cursor = conn.cursor()
    fields = []
    values = []
    for k in ['suggested_negative', 'match_type', 'scope', 'status']:
        if k in updates:
            fields.append(f"{k} = ?")
            values.append(updates[k])
    if fields:
        values.append(neg_id)
        cursor.execute(f"UPDATE negative_keywords SET {', '.join(fields)} WHERE id = ?", tuple(values))
        conn.commit()
    conn.close()

def clear_negative_keywords():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM negative_keywords')
    conn.commit()
    conn.close()

# Audit Log Operations
def save_audit_log(session_id, dataset_name, row_count, promote_count, block_count, ignore_count, review_count, total_spend):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute('''
        INSERT INTO audit_logs (session_id, dataset_name, row_count, promote_count, block_count, ignore_count, review_count, total_spend, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, dataset_name, row_count, promote_count, block_count, ignore_count, review_count, total_spend, now))
    conn.commit()
    conn.close()

def get_audit_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM audit_logs ORDER BY id DESC LIMIT 20')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Config Settings Operations
def get_config_setting(key, default_value=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config_settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row['value'])
        except Exception:
            return row['value']
    return default_value

def set_config_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    val_str = json.dumps(value) if not isinstance(value, str) else value
    cursor.execute('''
        INSERT INTO config_settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, val_str))
    conn.commit()
    conn.close()

# Initialize upon module load
init_db()

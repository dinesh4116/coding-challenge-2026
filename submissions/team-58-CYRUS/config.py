import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RAW_DATA_PATH = BASE_DIR / "search_terms_report.csv"
OUTPUT_CSV_PATH = PROCESSED_DATA_DIR / "search_terms_decision_ledger.csv"
DB_PATH = DATA_DIR / "searchguard.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

APP_TITLE = "SearchGuard AI"
APP_DESCRIPTION = "Evidence-Aware Search Term Triage & Decision Intelligence Platform"
API_PREFIX = "/api"

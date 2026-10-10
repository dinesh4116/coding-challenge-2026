import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_campaign_data():
    path = DATA_DIR / "campaign_data.csv"
    return pd.read_csv(path)


def load_security_data():
    path = DATA_DIR / "security_events.csv"
    return pd.read_csv(path)
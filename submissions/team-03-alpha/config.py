import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    SAMPLE_CSV = os.path.join(
        os.path.dirname(__file__),
        "data",
        "campaign_data.csv"
    )

    DB = dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password="mysql",
        database=os.getenv("DB_NAME", "campaign_anomaly"),
        charset="utf8mb4",
    )
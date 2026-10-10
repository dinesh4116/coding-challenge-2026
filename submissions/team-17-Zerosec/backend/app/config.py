"""Application settings read from environment variables.

Keeping configuration in one place means the CORS origins and upload limits
can be changed without touching code (e.g. CORS_ORIGINS for a deployed
frontend). Settings are read when the app is created, not at import time.
"""
import os
from dataclasses import dataclass, field

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


@dataclass(frozen=True)
class Settings:
    app_name: str = "PS-04 Campaign Anomaly Alerting"
    version: str = "0.1.0"
    cors_origins: list[str] = field(default_factory=list)
    max_upload_bytes: int = 10 * 1024 * 1024
    max_rows: int = 200_000


def get_settings() -> Settings:
    origins = os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    max_mb = float(os.environ.get("MAX_UPLOAD_MB", "10"))
    return Settings(
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        max_upload_bytes=int(max_mb * 1024 * 1024),
        max_rows=int(os.environ.get("MAX_ROWS", "200000")),
    )

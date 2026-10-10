import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import APP_TITLE, APP_DESCRIPTION, RAW_DATA_PATH, DB_PATH
from backend.app.database import engine, Base
from backend.app.pipeline.validator import DatasetValidator
from backend.app.pipeline.pipeline_runner import run_pipeline

from backend.app.api.overview import router as overview_router
from backend.app.api.profiling import router as profiling_router
from backend.app.api.records import router as records_router
from backend.app.api.campaigns import router as campaigns_router
from backend.app.api.duplicates import router as duplicates_router
from backend.app.api.reviews import router as reviews_router
from backend.app.api.audit import router as audit_router
from backend.app.api.export import router as export_router
from backend.app.api.evaluation import router as evaluation_router

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version="1.0.0"
)

# Enable CORS for React frontend (Vite default: http://localhost:5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(overview_router, prefix="/api")
app.include_router(profiling_router, prefix="/api")
app.include_router(records_router, prefix="/api")
app.include_router(campaigns_router, prefix="/api")
app.include_router(duplicates_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api")

@app.on_event("startup")
def startup_event():
    print("Initializing SearchGuard AI Backend...")
    # 1. Verify dataset path and schema at application startup
    validator = DatasetValidator(str(RAW_DATA_PATH))
    val_res = validator.validate()
    print(f"Startup validation: {val_res['total_rows']} rows verified in {val_res['file_path']}")

    # 2. Ensure SQLite DB tables are created
    Base.metadata.create_all(bind=engine)

    # 3. Check if DB has data; if empty, execute pipeline runner
    from backend.app.database import SessionLocal
    from backend.app.models import DecisionRecord
    db = SessionLocal()
    try:
        count = db.query(DecisionRecord).count()
        if count == 0:
            print("Database empty. Executing initial intelligence pipeline on 25,000 records...")
            run_pipeline(str(RAW_DATA_PATH), save_to_db=True)
        else:
            print(f"Database ready with {count} processed decision records.")
    finally:
        db.close()

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": APP_TITLE,
        "database": str(DB_PATH)
    }

@app.post("/api/pipeline/run")
def trigger_pipeline():
    """Manual trigger to re-run pipeline on the dataset."""
    df = run_pipeline(str(RAW_DATA_PATH), save_to_db=True)
    return {
        "status": "SUCCESS",
        "records_processed": len(df),
        "columns": list(df.columns)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

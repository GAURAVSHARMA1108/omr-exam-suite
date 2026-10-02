import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
OVERLAYS_DIR = STORAGE_DIR / "overlays"
PDFS_DIR = STORAGE_DIR / "pdfs"

for folder in [STORAGE_DIR, UPLOADS_DIR, OVERLAYS_DIR, PDFS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "OMR Exam Suite API"
    VERSION: str = "1.0.0"
    # PostgreSQL connection URL; fallback to local SQLite if Postgres is not configured
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{STORAGE_DIR / 'omr_suite.db'}"
    )
    SCANNER_BRIDGE_URL: str = os.getenv("SCANNER_BRIDGE_URL", "http://127.0.0.1:8765")
    CORS_ORIGINS: list[str] = ["*"]

settings = Settings()

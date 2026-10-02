from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import settings, STORAGE_DIR, OVERLAYS_DIR, UPLOADS_DIR, BASE_DIR
from app.database import init_db
from app.api import exams, grading, submissions

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Enable CORS for frontend and local bridge
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated overlays and uploads statically for preview
app.mount("/static/overlays", StaticFiles(directory=str(OVERLAYS_DIR)), name="overlays")
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Include Routers
app.include_router(exams.router)
app.include_router(grading.router)
app.include_router(submissions.router)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "database": settings.DATABASE_URL.split("://")[0]
    }

# Mount built frontend SPA if available
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    from fastapi.responses import FileResponse
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't intercept API or static requests
        if full_path.startswith("api") or full_path.startswith("static"):
            return None
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")


from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.database import init_db
from app.scheduler.scheduler import start_scheduler, shutdown_scheduler
from app.routers import auth, clock, audit, applications, evc, compliance, notifications, reports, dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables & SQLite append-only triggers on startup
    init_db()
    # Start APScheduler background scan engine
    start_scheduler()
    yield
    # Shutdown scheduler cleanly
    shutdown_scheduler()

app = FastAPI(
    title="AICTE Approval Workflow Automation & Compliance System",
    description="Backend API for AICTE Approval Automation, Compliance Monitoring, and Alert Management. "
                "Automated alerts support, but do not replace, statutory scrutiny and decisions of the competent authority.",
    version="1.0.0",
    lifespan=lifespan
)

origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(clock.router)
app.include_router(audit.router)
app.include_router(applications.router)
app.include_router(evc.router)
app.include_router(compliance.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(dashboard.router)

@app.get("/api/health")
def root():
    return {
        "system": "AICTE Approval Automation & Compliance Monitoring System",
        "status": "operational",
        "disclaimer": "Automated alerts support, but do not replace, statutory scrutiny and decisions of the competent authority.",
        "version": "1.0.0"
    }

_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return FileResponse(_DIST / "index.html")

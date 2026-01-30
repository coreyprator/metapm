"""
MetaPM - Meta Project Manager
FastAPI Application Entry Point
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api import tasks, projects, categories, methodology, capture, calendar, themes
from app.core.config import settings
from transactions import router as transactions_router
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MetaPM",
    description="Cross-project task management system for Corey's 2026 projects",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Log startup to verify deployment
logger.info(f"=" * 80)
logger.info(f"MetaPM v{settings.VERSION} STARTING UP")
logger.info(f"This log message added to verify code deployment")
logger.info(f"=" * 80)

# Redirect root to dashboard
@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/static/dashboard.html")

# CORS middleware for mobile/web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(methodology.router, prefix="/api/methodology", tags=["Methodology"])
app.include_router(capture.router, prefix="/api/capture", tags=["Quick Capture"])
app.include_router(transactions_router, prefix="/api/transactions", tags=["Transactions & Analytics"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(themes.router, prefix="/api/themes", tags=["Themes"])


# Define static_dir early for use in routes
static_dir = Path(__file__).parent.parent / "static"


# Define direct routes BEFORE mounting static files
@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "test": "PINEAPPLE-99999",
        "version": settings.VERSION,
        "build": settings.BUILD,
    }


@app.get("/debug/routes")
async def list_routes():
    """Debug: List all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if hasattr(route, 'methods') else []
            })
    return {"routes": routes, "count": len(routes)}


@app.get("/api/version")
async def get_version():
    """API version information"""
    return {"version": settings.VERSION, "build": settings.BUILD, "name": "MetaPM"}


@app.get("/capture.html")
async def capture_page():
    """Serve the voice capture PWA"""
    from fastapi.responses import FileResponse
    capture_file = static_dir / "capture.html"
    if capture_file.exists():
        return FileResponse(str(capture_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Capture page not found")


# Mount static files LAST (after all route definitions)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

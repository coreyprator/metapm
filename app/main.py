"""
MetaPM - Meta Project Manager
FastAPI Application Entry Point
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api import tasks, projects, categories, methodology, capture, calendar, themes, backlog, mcp, roadmap, handoff_lifecycle, conductor
from app.core.config import settings
from app.core.migrations import run_migrations
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
logger.info(f"=" * 80)

# Run database migrations
try:
    run_migrations()
except Exception as e:
    logger.warning(f"Migration warning (non-fatal): {e}")

# Redirect root to dashboard
@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/static/dashboard.html")

# CORS middleware for mobile/web access
# allow_credentials=False allows wildcard origins, which is needed for file:// (null origin)
# We use API keys instead of cookies, so credentials are not needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom validation error handler for better 422 messages (HO-N3O4)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error.get("loc", []))
        errors.append(f"{field}: {error.get('msg', 'unknown error')} (type={error.get('type', '?')})")
    detail = "; ".join(errors)
    logger.warning(f"422 Validation Error on {request.method} {request.url.path}: {detail}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": detail,
            "hint": "Check field names and types. See /docs for schema."
        }
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
app.include_router(backlog.router, prefix="/api/backlog", tags=["Backlog"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP"])
app.include_router(roadmap.router, prefix="/api", tags=["Roadmap"])
app.include_router(handoff_lifecycle.router, prefix="/api", tags=["Handoff Lifecycle"])
app.include_router(conductor.router, tags=["Conductor"])


# Define static_dir early for use in routes
static_dir = Path(__file__).parent.parent / "static"


# Define direct routes BEFORE mounting static files
@app.get("/health")
@app.head("/health")
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


@app.get("/handoffs.html")
async def handoffs_page():
    """Serve the Handoff Bridge dashboard"""
    from fastapi.responses import FileResponse
    handoffs_file = static_dir / "handoffs.html"
    if handoffs_file.exists():
        return FileResponse(str(handoffs_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Handoffs page not found")


@app.get("/roadmap.html")
async def roadmap_page():
    """Serve the Project Roadmap dashboard"""
    from fastapi.responses import FileResponse
    roadmap_file = static_dir / "roadmap.html"
    if roadmap_file.exists():
        return FileResponse(str(roadmap_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Roadmap page not found")


@app.get("/compare/{handoff_id}")
async def compare_page(handoff_id: str):
    """Serve the Handoff Comparison page (HO-A1B2)"""
    from fastapi.responses import FileResponse
    compare_file = static_dir / "compare.html"
    if compare_file.exists():
        return FileResponse(str(compare_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Compare page not found")


# Mount static files LAST (after all route definitions)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

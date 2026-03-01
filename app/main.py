"""
MetaPM - Meta Project Manager
FastAPI Application Entry Point
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError

from app.api import tasks, projects, categories, methodology, capture, calendar, themes, backlog, mcp, roadmap, handoff_lifecycle, conductor, rag, lessons
from app.core.config import settings
from app.core.migrations import run_migrations
from app.schemas.mcp import UATDirectSubmit, UATDirectSubmitResponse
from transactions import router as transactions_router
import logging
import traceback

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
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
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


# Standard C: Global exception handler — catches unhandled exceptions, returns structured JSON
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_detail = str(exc)
    traceback_str = traceback.format_exc()
    logger.error(f"Unhandled exception on {request.method} {request.url}: {error_detail}\n{traceback_str}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": error_detail,
            "path": str(request.url.path)
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
app.include_router(rag.router, prefix="/api", tags=["Portfolio RAG"])
app.include_router(lessons.router, prefix="/api", tags=["Lessons"])


# Define static_dir early for use in routes
static_dir = Path(__file__).parent.parent / "static"


# Define direct routes BEFORE mounting static files
@app.get("/health")
@app.head("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "build": settings.BUILD,
    }


@app.get("/architecture")
async def architecture_redirect():
    return RedirectResponse(
        url="https://storage.googleapis.com/corey-handoff-bridge/project-methodology/docs/Development_System_Architecture.html",
        status_code=302
    )


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


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon from static directory."""
    favicon_file = static_dir / "favicon.ico"
    if favicon_file.exists():
        return FileResponse(str(favicon_file), media_type="image/x-icon")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.options("/api/uat/submit")
async def api_uat_submit_preflight():
    """Handle browser preflight for UAT submit alias."""
    return JSONResponse(status_code=204, content={})


@app.post("/api/uat/submit", response_model=UATDirectSubmitResponse, status_code=201)
async def api_uat_submit_alias(uat: UATDirectSubmit):
    """Public alias for direct UAT submission used by checklist templates."""
    return await mcp.submit_uat_direct(uat)


@app.post("/api/uat/direct-submit", response_model=UATDirectSubmitResponse, status_code=201)
async def api_uat_direct_submit_alias(uat: UATDirectSubmit):
    """Backward-compatible API alias for direct UAT submission."""
    return await mcp.submit_uat_direct(uat)


# Mount static files LAST (after all route definitions)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

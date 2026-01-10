"""
MetaPM - Meta Project Manager
FastAPI Application Entry Point
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api import tasks, projects, categories, methodology, capture
from app.core.config import settings

app = FastAPI(
    title="MetaPM",
    description="Cross-project task management system for Corey's 2026 projects",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

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

# Serve static files (PWA, manifest, etc.)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Health check and API info"""
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy"}

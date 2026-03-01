"""
Portfolio RAG proxy endpoints (MP-MS3 Phase 4).
Proxies requests to the Portfolio RAG service.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

RAG_BASE = settings.PORTFOLIO_RAG_URL.rstrip("/")
TIMEOUT = 15.0


@router.get("/rag/query")
async def rag_query(q: str = Query(..., min_length=1)):
    """Proxy search query to Portfolio RAG."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{RAG_BASE}/query", params={"q": q})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"RAG query proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"RAG service error: {e}")


@router.get("/rag/documents")
async def rag_documents(repo: Optional[str] = None, doc_type: Optional[str] = None):
    """Proxy document listing to Portfolio RAG."""
    try:
        params = {}
        if repo:
            params["repo"] = repo
        if doc_type:
            params["doc_type"] = doc_type
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{RAG_BASE}/documents", params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"RAG documents proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"RAG service error: {e}")


@router.get("/rag/latest/{doc_type}")
async def rag_latest(doc_type: str, repo: Optional[str] = None):
    """Proxy latest document query to Portfolio RAG."""
    try:
        params = {}
        if repo:
            params["repo"] = repo
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{RAG_BASE}/latest/{doc_type}", params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"RAG latest proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"RAG service error: {e}")


@router.get("/rag/checkpoints")
async def rag_checkpoints():
    """Proxy checkpoint listing to Portfolio RAG."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{RAG_BASE}/checkpoints")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"RAG checkpoints proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"RAG service error: {e}")

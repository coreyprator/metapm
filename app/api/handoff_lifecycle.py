"""
Handoff Lifecycle API Endpoints (HO-A1B2)
Tracks the full lifecycle of handoffs from spec to completion.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.database import execute_query
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class HandoffRequestCreate(BaseModel):
    id: str  # HO-XXXX
    project: str
    roadmap_id: Optional[str] = None
    request_type: str  # Requirement, Bug, UAT, Enhancement, Hotfix
    title: str
    description: Optional[str] = None
    spec_handoff_url: Optional[str] = None


class HandoffStatusUpdate(BaseModel):
    status: str  # SPEC, PENDING, DELIVERED, UAT, PASSED, FAILED
    completion_handoff_url: Optional[str] = None


class HandoffCompletion(BaseModel):
    status: str  # COMPLETE, PARTIAL, BLOCKED
    commit_hash: Optional[str] = None
    completion_handoff_url: Optional[str] = None
    notes: Optional[str] = None


class RoadmapHandoffLink(BaseModel):
    handoff_id: str
    relationship: str  # IMPLEMENTS, FIXES, TESTS, ENHANCES


# ============================================================================
# Handoff CRUD Endpoints
# ============================================================================

@router.post("/handoffs")
async def create_handoff(handoff: HandoffRequestCreate):
    """Create a new handoff request."""
    try:
        execute_query("""
            INSERT INTO handoff_requests
            (id, project, roadmap_id, request_type, title, description, spec_handoff_url, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'SPEC')
        """, (
            handoff.id,
            handoff.project,
            handoff.roadmap_id,
            handoff.request_type,
            handoff.title,
            handoff.description,
            handoff.spec_handoff_url
        ), fetch="none")

        # If roadmap_id provided, create the link
        if handoff.roadmap_id:
            try:
                execute_query("""
                    INSERT INTO roadmap_handoffs (roadmap_id, handoff_id, relationship)
                    VALUES (?, ?, 'IMPLEMENTS')
                """, (handoff.roadmap_id, handoff.id), fetch="none")
            except Exception as e:
                logger.warning(f"Could not link to roadmap: {e}")

        return {"success": True, "id": handoff.id, "status": "SPEC"}

    except Exception as e:
        logger.error(f"Failed to create handoff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/handoffs/{handoff_id}")
async def get_handoff(handoff_id: str):
    """Get full handoff details with completions."""
    try:
        # Get handoff request
        handoff = execute_query("""
            SELECT * FROM handoff_requests WHERE id = ?
        """, (handoff_id,), fetch="one")

        if not handoff:
            raise HTTPException(status_code=404, detail=f"Handoff {handoff_id} not found")

        # Get completions
        completions = execute_query("""
            SELECT * FROM handoff_completions
            WHERE handoff_id = ?
            ORDER BY completed_at DESC
        """, (handoff_id,), fetch="all") or []

        # Get linked roadmap items
        roadmap_links = execute_query("""
            SELECT roadmap_id, relationship, created_at
            FROM roadmap_handoffs
            WHERE handoff_id = ?
        """, (handoff_id,), fetch="all") or []

        return {
            "handoff": dict(handoff),
            "completions": [dict(c) for c in completions],
            "roadmap_links": [dict(r) for r in roadmap_links]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get handoff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/handoffs/{handoff_id}/status")
async def update_handoff_status(handoff_id: str, update: HandoffStatusUpdate):
    """Update handoff status."""
    try:
        execute_query("""
            UPDATE handoff_requests
            SET status = ?, updated_at = GETDATE()
            WHERE id = ?
        """, (update.status, handoff_id), fetch="none")

        return {"success": True, "id": handoff_id, "status": update.status}

    except Exception as e:
        logger.error(f"Failed to update handoff status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/handoffs/{handoff_id}/complete")
async def record_completion(handoff_id: str, completion: HandoffCompletion):
    """Record a completion response from CC."""
    try:
        # Insert completion record
        execute_query("""
            INSERT INTO handoff_completions
            (handoff_id, status, commit_hash, completion_handoff_url, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            handoff_id,
            completion.status,
            completion.commit_hash,
            completion.completion_handoff_url,
            completion.notes
        ), fetch="none")

        # Update handoff request status based on completion status
        new_status = "DELIVERED" if completion.status == "COMPLETE" else "PENDING"
        execute_query("""
            UPDATE handoff_requests
            SET status = ?, updated_at = GETDATE()
            WHERE id = ?
        """, (new_status, handoff_id), fetch="none")

        return {
            "success": True,
            "handoff_id": handoff_id,
            "completion_status": completion.status,
            "handoff_status": new_status
        }

    except Exception as e:
        logger.error(f"Failed to record completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/handoffs")
async def list_handoffs(
    project: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100)
):
    """List handoff requests with optional filters."""
    try:
        query = f"SELECT TOP {limit} * FROM handoff_requests WHERE 1=1"
        params = []

        if project:
            query += " AND project = ?"
            params.append(project)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        handoffs = execute_query(query, tuple(params), fetch="all") or []

        return {"handoffs": [dict(h) for h in handoffs], "count": len(handoffs)}

    except Exception as e:
        logger.error(f"Failed to list handoffs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Roadmap-Handoff Linking Endpoints
# ============================================================================

@router.get("/roadmap/{roadmap_id}/handoffs")
async def get_roadmap_handoffs(roadmap_id: str):
    """Get all handoffs linked to a roadmap item."""
    try:
        handoffs = execute_query("""
            SELECT
                h.*,
                c.completed_at,
                c.status as completion_status,
                c.commit_hash,
                rh.relationship
            FROM handoff_requests h
            JOIN roadmap_handoffs rh ON h.id = rh.handoff_id
            LEFT JOIN (
                SELECT handoff_id, completed_at, status, commit_hash,
                       ROW_NUMBER() OVER (PARTITION BY handoff_id ORDER BY completed_at DESC) as rn
                FROM handoff_completions
            ) c ON h.id = c.handoff_id AND c.rn = 1
            WHERE rh.roadmap_id = ?
            ORDER BY h.created_at DESC
        """, (roadmap_id,), fetch="all") or []

        return {"roadmap_id": roadmap_id, "handoffs": [dict(h) for h in handoffs]}

    except Exception as e:
        logger.error(f"Failed to get roadmap handoffs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roadmap/{roadmap_id}/handoffs")
async def link_handoff_to_roadmap(roadmap_id: str, link: RoadmapHandoffLink):
    """Link a handoff to a roadmap item."""
    try:
        execute_query("""
            INSERT INTO roadmap_handoffs (roadmap_id, handoff_id, relationship)
            VALUES (?, ?, ?)
        """, (roadmap_id, link.handoff_id, link.relationship), fetch="none")

        return {"success": True, "roadmap_id": roadmap_id, "handoff_id": link.handoff_id}

    except Exception as e:
        logger.error(f"Failed to link handoff to roadmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

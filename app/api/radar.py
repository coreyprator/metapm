"""
MetaPM Project Radar API
PABUGS2: Filtered project-radar endpoint for Personal Assistant.
Returns only real, recent actionable items — no seeds, no stale prompts.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(x_api_key: Optional[str] = Depends(api_key_header)) -> bool:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    expected = settings.MCP_API_KEY or settings.API_KEY
    if not expected:
        raise HTTPException(status_code=503, detail="API key not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


@router.get("/project-radar")
async def get_project_radar(_: bool = Depends(verify_api_key)):
    """
    PABUGS2: Filtered project radar for Personal Assistant.

    Returns three queues — all filtered to last 14 days and excluding seed prompts:
      - approve_prompts: draft prompts with estimated_hours > 0.1
      - ready_to_launch: approved prompts within 14 days
      - run_uats: requirements at uat_ready status
    """
    # Queue 1: Draft prompts awaiting PL approval (real sprints only, last 14 days)
    approve_rows = execute_query("""
        SELECT TOP 10
            p.pth,
            p.sprint_id,
            p.estimated_hours,
            COALESCE(proj.name, p.project_id) AS project,
            COALESCE(proj.emoji, '') AS emoji
        FROM cc_prompts p
        LEFT JOIN roadmap_projects proj ON p.project_id = proj.id
        WHERE p.status = 'draft'
          AND p.estimated_hours > 0.1
          AND p.updated_at > DATEADD(day, -14, GETUTCDATE())
        ORDER BY p.updated_at DESC
    """, fetch="all") or []

    approve_prompts = [
        {
            "pth": r["pth"],
            "project": r["project"] or "",
            "emoji": r["emoji"] or "",
            "title": r["sprint_id"] or r["pth"],
            "estimated_hours": r["estimated_hours"],
            "review_url": f"https://metapm.rentyourcio.com/prompts/{r['pth']}",
        }
        for r in approve_rows
    ]

    # Queue 2: Approved prompts ready to launch (last 14 days)
    launch_rows = execute_query("""
        SELECT TOP 10
            p.pth,
            p.sprint_id,
            p.estimated_hours,
            COALESCE(proj.name, p.project_id) AS project,
            COALESCE(proj.emoji, '') AS emoji
        FROM cc_prompts p
        LEFT JOIN roadmap_projects proj ON p.project_id = proj.id
        WHERE p.status = 'approved'
          AND p.approved_at > DATEADD(day, -14, GETUTCDATE())
        ORDER BY p.approved_at DESC
    """, fetch="all") or []

    ready_to_launch = [
        {
            "pth": r["pth"],
            "project": r["project"] or "",
            "emoji": r["emoji"] or "",
            "title": r["sprint_id"] or r["pth"],
            "estimated_hours": r["estimated_hours"],
            "review_url": f"https://metapm.rentyourcio.com/prompts/{r['pth']}",
        }
        for r in launch_rows
    ]

    # Queue 3: Requirements at uat_ready — PL runs UATs (last 14 days)
    uat_rows = execute_query("""
        SELECT TOP 10
            r.pth,
            r.code,
            r.title,
            r.uat_url,
            COALESCE(proj.name, r.project_id) AS project,
            COALESCE(proj.emoji, '') AS emoji
        FROM roadmap_requirements r
        LEFT JOIN roadmap_projects proj ON r.project_id = proj.id
        WHERE r.status = 'uat_ready'
          AND r.updated_at > DATEADD(day, -14, GETUTCDATE())
        ORDER BY r.updated_at DESC
    """, fetch="all") or []

    run_uats = [
        {
            "pth": r["pth"] or r["code"] or "",
            "project": r["project"] or "",
            "emoji": r["emoji"] or "",
            "req": r["code"] or "",
            "title": r["title"] or "",
            "uat_url": r["uat_url"] or "",
        }
        for r in uat_rows
    ]

    # Queue 4 (MM16-REQ-003): Active CC jobs — executing prompts with PTH
    active_rows = execute_query("""
        SELECT TOP 10
            p.pth,
            p.sprint_id,
            COALESCE(proj.name, p.project_id) AS project,
            COALESCE(proj.emoji, '') AS emoji,
            p.updated_at
        FROM cc_prompts p
        LEFT JOIN roadmap_projects proj ON p.project_id = proj.id
        WHERE p.status IN ('executing', 'sent')
          AND p.updated_at > DATEADD(day, -3, GETUTCDATE())
        ORDER BY p.updated_at DESC
    """, fetch="all") or []

    active_jobs = [
        {
            "pth": r["pth"],
            "project": r["project"] or "",
            "emoji": r["emoji"] or "",
            "title": r["sprint_id"] or r["pth"],
            "status": "Running",
            "started": r["updated_at"],
        }
        for r in active_rows
    ]

    logger.info(
        f"[PABUGS2] project-radar: {len(approve_prompts)} to approve, "
        f"{len(ready_to_launch)} ready to launch, {len(run_uats)} UATs to run, "
        f"{len(active_jobs)} active jobs"
    )

    return {
        "approve_prompts": approve_prompts,
        "ready_to_launch": ready_to_launch,
        "run_uats": run_uats,
        "active_jobs": active_jobs,
    }

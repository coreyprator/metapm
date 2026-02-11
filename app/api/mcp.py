"""
MetaPM MCP API Router
Native REST endpoints for Model Context Protocol integration.
Allows Claude Code to interact directly with handoffs and tasks.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Response
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.database import execute_query
from app.schemas.mcp import (
    HandoffCreate, HandoffUpdate, HandoffResponse, HandoffListResponse,
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    LogEntry, LogResponse, LogEntryType,
    HandoffDirection, HandoffStatus, TaskStatus, TaskPriority,
    UATSubmit, UATResult, UATHistoryResponse, UATStatus,
    UATDirectSubmit, UATDirectSubmitResponse,
    UATListItem, UATListResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    x_api_key: Optional[str] = Depends(api_key_header),
    authorization: Optional[str] = Header(None)
) -> bool:
    """
    Verify API key from X-API-Key header or Authorization: Bearer header.
    Returns True if valid, raises HTTPException if invalid.
    """
    api_key = None

    # Check X-API-Key header first
    if x_api_key:
        api_key = x_api_key
    # Check Authorization: Bearer header
    elif authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    if not settings.MCP_API_KEY:
        logger.warning("MCP_API_KEY not configured - rejecting request")
        raise HTTPException(status_code=500, detail="MCP API key not configured")

    if api_key != settings.MCP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return True


def _parse_json_field(value: Optional[str]) -> Optional[dict]:
    """Parse JSON string field to dict."""
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _parse_tags_field(value: Optional[str]) -> Optional[List[str]]:
    """Parse JSON array string field to list."""
    if not value:
        return None
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return result
        return None
    except (json.JSONDecodeError, TypeError):
        return None


# ============================================
# HANDOFF ENDPOINTS
# ============================================

@router.post("/handoffs", response_model=HandoffResponse, status_code=201)
async def create_handoff(
    handoff: HandoffCreate,
    _: bool = Depends(verify_api_key)
):
    """Create a new handoff."""
    try:
        metadata_json = json.dumps(handoff.metadata) if handoff.metadata else None

        result = execute_query("""
            INSERT INTO mcp_handoffs (project, task, direction, content, metadata, response_to)
            OUTPUT INSERTED.id, INSERTED.project, INSERTED.task, INSERTED.direction,
                   INSERTED.status, INSERTED.metadata, INSERTED.response_to,
                   INSERTED.created_at, INSERTED.updated_at
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            handoff.project,
            handoff.task,
            handoff.direction.value,
            handoff.content,
            metadata_json,
            handoff.response_to
        ), fetch="one")

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create handoff")

        handoff_id = str(result['id'])
        public_url = f"https://metapm.rentyourcio.com/mcp/handoffs/{handoff_id}/content"

        return HandoffResponse(
            id=handoff_id,
            project=result['project'],
            task=result['task'],
            direction=HandoffDirection(result['direction']),
            status=HandoffStatus(result['status']),
            metadata=_parse_json_field(result['metadata']),
            response_to=str(result['response_to']) if result['response_to'] else None,
            public_url=public_url,
            created_at=result['created_at'],
            updated_at=result['updated_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating handoff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/handoffs", response_model=HandoffListResponse)
async def list_handoffs(
    project: Optional[str] = Query(None),
    status: Optional[HandoffStatus] = Query(None),
    direction: Optional[HandoffDirection] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    _: bool = Depends(verify_api_key)
):
    """List handoffs with optional filters."""
    try:
        # Build query with filters
        where_clauses = []
        params = []

        if project:
            where_clauses.append("project = ?")
            params.append(project)
        if status:
            where_clauses.append("status = ?")
            params.append(status.value)
        if direction:
            where_clauses.append("direction = ?")
            params.append(direction.value)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_result = execute_query(
            f"SELECT COUNT(*) as total FROM mcp_handoffs WHERE {where_sql}",
            tuple(params) if params else None,
            fetch="one"
        )
        total = count_result['total'] if count_result else 0

        # Get paginated results
        params.extend([offset, limit])
        results = execute_query(f"""
            SELECT id, project, task, direction, status, metadata, response_to, created_at, updated_at
            FROM mcp_handoffs
            WHERE {where_sql}
            ORDER BY created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, tuple(params), fetch="all")

        handoffs = []
        for row in (results or []):
            public_url = f"https://metapm.rentyourcio.com/mcp/handoffs/{row['id']}/content"
            handoffs.append(HandoffResponse(
                id=str(row['id']),
                project=row['project'],
                task=row['task'],
                direction=HandoffDirection(row['direction']),
                status=HandoffStatus(row['status']),
                metadata=_parse_json_field(row['metadata']),
                response_to=str(row['response_to']) if row['response_to'] else None,
                public_url=public_url,
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))

        return HandoffListResponse(
            handoffs=handoffs,
            total=total,
            has_more=(offset + limit) < total
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing handoffs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# DASHBOARD ENDPOINTS (Phase 4) - Must come before {handoff_id} wildcard
# ============================================

# Project emoji mapping
PROJECT_EMOJI = {
    'ArtForge': '🟠',
    'artforge': '🟠',
    'HarmonyLab': '🔵',
    'harmonylab': '🔵',
    'Super-Flashcards': '🟡',
    'super-flashcards': '🟡',
    'MetaPM': '🔴',
    'metapm': '🔴',
    'Etymython': '🟣',
    'etymython': '🟣',
    'project-methodology': '🟢',
    'Security': '🔒',
}


@router.get("/handoffs/dashboard")
async def dashboard_handoffs(
    project: Optional[str] = Query(None),
    status: Optional[HandoffStatus] = Query(None),
    direction: Optional[HandoffDirection] = Query(None),
    gcs_sync: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=100)
):
    """
    Dashboard-specific handoffs endpoint (PUBLIC - no auth for dashboard viewing).
    Returns handoffs with additional fields for display.
    """
    try:
        where_clauses = []
        params = []

        if project:
            where_clauses.append("project = ?")
            params.append(project)
        if status:
            where_clauses.append("status = ?")
            params.append(status.value)
        if direction:
            where_clauses.append("direction = ?")
            params.append(direction.value)
        if search:
            where_clauses.append("(task LIKE ? OR content LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if gcs_sync:
            if gcs_sync == "synced":
                where_clauses.append("gcs_synced = 1")
            elif gcs_sync == "pending":
                where_clauses.append("(gcs_synced = 0 OR gcs_synced IS NULL)")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Validate sort field
        valid_sorts = ["created_at", "project", "task", "status", "direction"]
        if sort not in valid_sorts:
            sort = "created_at"

        order_sql = "DESC" if order.lower() == "desc" else "ASC"
        offset = (page - 1) * limit

        # Get total count
        count_result = execute_query(
            f"SELECT COUNT(*) as total FROM mcp_handoffs WHERE {where_sql}",
            tuple(params) if params else None,
            fetch="one"
        )
        total = count_result['total'] if count_result else 0

        # Get paginated results
        params.extend([offset, limit])
        results = execute_query(f"""
            SELECT id, project, task, title, direction, status, content, source,
                   gcs_path, gcs_url, gcs_synced, from_entity, to_entity,
                   version, git_commit, git_verified, compliance_score,
                   uat_status, uat_passed, uat_failed, uat_date,
                   created_at, updated_at
            FROM mcp_handoffs
            WHERE {where_sql}
            ORDER BY {sort} {order_sql}
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, tuple(params), fetch="all")

        handoffs = []
        for row in (results or []):
            # Get first ~200 chars as preview
            content = row['content'] or ''
            preview = content[:200] + '...' if len(content) > 200 else content

            # Get emoji for project
            emoji = PROJECT_EMOJI.get(row['project'], '📦')

            handoffs.append({
                "id": str(row['id']),
                "project": row['project'],
                "project_emoji": emoji,
                "task": row['task'],
                "title": row.get('title'),
                "direction": row['direction'],
                "status": row['status'],
                "preview": preview,
                "source": row.get('source') or 'api',
                "from_entity": row.get('from_entity'),
                "to_entity": row.get('to_entity'),
                "version": row.get('version'),
                "git_commit": row.get('git_commit'),
                "git_verified": bool(row.get('git_verified')),
                "gcs_synced": bool(row.get('gcs_synced')),
                "gcs_url": row.get('gcs_url'),
                "compliance_score": row.get('compliance_score', 100),
                "uat_status": row.get('uat_status'),
                "uat_passed": row.get('uat_passed'),
                "uat_failed": row.get('uat_failed'),
                "uat_date": row['uat_date'].isoformat() if row.get('uat_date') else None,
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "public_url": f"https://metapm.rentyourcio.com/mcp/handoffs/{row['id']}/content"
            })

        return {
            "handoffs": handoffs,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error in dashboard handoffs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/handoffs/stats")
async def handoff_stats():
    """
    Get handoff statistics (PUBLIC - no auth for dashboard viewing).
    Returns total counts by project and status with enhanced stats.
    """
    try:
        # Total count
        total_result = execute_query(
            "SELECT COUNT(*) as total FROM mcp_handoffs",
            fetch="one"
        )
        total = total_result['total'] if total_result else 0

        # By project with enhanced stats
        project_results = execute_query("""
            SELECT project,
                   COUNT(*) as total,
                   SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN status IN ('processed', 'archived') THEN 1 ELSE 0 END) as done,
                   SUM(CASE WHEN gcs_synced = 1 THEN 1 ELSE 0 END) as synced
            FROM mcp_handoffs
            GROUP BY project
            ORDER BY total DESC
        """, fetch="all")
        by_project = {}
        for row in (project_results or []):
            by_project[row['project']] = {
                "total": row['total'],
                "pending": row['pending'] or 0,
                "done": row['done'] or 0,
                "synced": row['synced'] or 0,
                "emoji": PROJECT_EMOJI.get(row['project'], '📦')
            }

        # By status
        status_results = execute_query("""
            SELECT status, COUNT(*) as count
            FROM mcp_handoffs
            GROUP BY status
        """, fetch="all")
        by_status = {row['status']: row['count'] for row in (status_results or [])}

        # By direction
        direction_results = execute_query("""
            SELECT direction, COUNT(*) as count
            FROM mcp_handoffs
            GROUP BY direction
        """, fetch="all")
        by_direction = {row['direction']: row['count'] for row in (direction_results or [])}

        # This week
        week_result = execute_query("""
            SELECT COUNT(*) as count FROM mcp_handoffs
            WHERE created_at >= DATEADD(day, -7, GETDATE())
        """, fetch="one")
        this_week = week_result['count'] if week_result else 0

        # GCS sync status
        sync_result = execute_query("""
            SELECT
                SUM(CASE WHEN gcs_synced = 1 THEN 1 ELSE 0 END) as synced,
                SUM(CASE WHEN gcs_synced = 0 OR gcs_synced IS NULL THEN 1 ELSE 0 END) as pending
            FROM mcp_handoffs
        """, fetch="one")

        return {
            "total": total,
            "this_week": this_week,
            "by_project": by_project,
            "by_status": by_status,
            "by_direction": by_direction,
            "gcs_sync_status": {
                "synced": sync_result['synced'] or 0 if sync_result else 0,
                "pending": sync_result['pending'] or 0 if sync_result else 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting handoff stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/handoffs/sync")
async def trigger_sync(
    _: bool = Depends(verify_api_key)
):
    """
    Trigger manual GCS bucket sync (requires auth).
    Imports handoffs from gs://corey-handoff-bridge/*/outbox/*.md
    """
    try:
        from app.jobs.sync_gcs_handoffs import sync_gcs_handoffs
        summary = sync_gcs_handoffs()
        return {
            "message": "Sync completed",
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error syncing GCS handoffs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/handoffs/export/log")
async def export_log(
    project: Optional[str] = Query(None),
    format: str = Query("markdown")
):
    """
    Generate HANDOFF_LOG.md from SQL data (PUBLIC - no auth).
    Returns markdown content that can be saved to GDrive.
    """
    try:
        from app.services.handoff_service import generate_log_markdown

        if not project:
            raise HTTPException(status_code=400, detail="project parameter required")

        md = generate_log_markdown(project)

        if format == "json":
            return {"project": project, "content": md}

        return Response(content=md, media_type="text/markdown")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# UAT ENDPOINTS
# ============================================

@router.post("/handoffs/{handoff_id}/uat", response_model=UATResult, status_code=201)
async def submit_uat_results(
    handoff_id: str,
    uat: UATSubmit,
    _: bool = Depends(verify_api_key)
):
    """
    Submit UAT results for a handoff (requires auth).
    Updates handoff status based on UAT result.
    """
    try:
        # Verify handoff exists
        handoff = execute_query(
            "SELECT id, status FROM mcp_handoffs WHERE id = ?",
            (handoff_id,),
            fetch="one"
        )
        if not handoff:
            raise HTTPException(status_code=404, detail="Handoff not found")

        # Insert UAT result
        result = execute_query("""
            INSERT INTO uat_results (
                handoff_id, status, total_tests, passed, failed,
                notes_count, results_text, checklist_path
            )
            OUTPUT INSERTED.id, INSERTED.handoff_id, INSERTED.status,
                   INSERTED.total_tests, INSERTED.passed, INSERTED.failed,
                   INSERTED.notes_count, INSERTED.tested_by, INSERTED.tested_at,
                   INSERTED.checklist_path
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            handoff_id,
            uat.status.value,
            uat.total_tests,
            uat.passed,
            uat.failed,
            uat.notes_count or 0,
            uat.results_text,
            uat.checklist_path
        ), fetch="one")

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create UAT result")

        # Update handoff status and UAT fields
        new_status = "done" if uat.status == UATStatus.PASSED else "needs_fixes"
        execute_query("""
            UPDATE mcp_handoffs
            SET status = ?,
                uat_status = ?,
                uat_passed = ?,
                uat_failed = ?,
                uat_date = GETUTCDATE(),
                updated_at = GETUTCDATE()
            WHERE id = ?
        """, (new_status, uat.status.value, uat.passed, uat.failed, handoff_id), fetch="none")

        return UATResult(
            id=str(result['id']),
            handoff_id=str(result['handoff_id']),
            status=UATStatus(result['status']),
            total_tests=result['total_tests'],
            passed=result['passed'],
            failed=result['failed'],
            notes_count=result['notes_count'],
            tested_by=result['tested_by'],
            tested_at=result['tested_at'],
            checklist_path=result['checklist_path']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting UAT: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/handoffs/{handoff_id}/uat", response_model=UATHistoryResponse)
async def get_uat_history(handoff_id: str):
    """
    Get UAT history for a handoff (PUBLIC - no auth for dashboard viewing).
    Returns all UAT attempts for the handoff.
    """
    try:
        # Verify handoff exists
        handoff = execute_query(
            "SELECT id FROM mcp_handoffs WHERE id = ?",
            (handoff_id,),
            fetch="one"
        )
        if not handoff:
            raise HTTPException(status_code=404, detail="Handoff not found")

        # Get UAT results
        results = execute_query("""
            SELECT id, handoff_id, status, total_tests, passed, failed,
                   notes_count, results_text, tested_by, tested_at, checklist_path
            FROM uat_results
            WHERE handoff_id = ?
            ORDER BY tested_at DESC
        """, (handoff_id,), fetch="all")

        attempts = []
        latest_status = None
        for row in (results or []):
            if latest_status is None:
                latest_status = UATStatus(row['status'])
            attempts.append(UATResult(
                id=str(row['id']),
                handoff_id=str(row['handoff_id']),
                status=UATStatus(row['status']),
                total_tests=row['total_tests'],
                passed=row['passed'],
                failed=row['failed'],
                notes_count=row['notes_count'],
                results_text=row['results_text'],
                tested_by=row['tested_by'],
                tested_at=row['tested_at'],
                checklist_path=row['checklist_path']
            ))

        return UATHistoryResponse(
            handoff_id=handoff_id,
            uat_attempts=attempts,
            latest_status=latest_status
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting UAT history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/uat/submit", response_model=UATDirectSubmitResponse, status_code=201)
async def submit_uat_direct(uat: UATDirectSubmit):
    """
    Submit UAT results directly from HTML checklist (PUBLIC - no auth required).
    Creates or finds a handoff for the project/version, then adds UAT result.
    Designed for file:// origin access from local HTML checklists.
    """
    try:
        # Build task identifier from version + feature
        task_id = f"v{uat.version}"
        if uat.feature:
            task_id = f"{task_id}-{uat.feature.lower().replace(' ', '-')}"

        # Look for existing handoff for this project/version
        handoff = execute_query("""
            SELECT id, status FROM mcp_handoffs
            WHERE project = ? AND task LIKE ?
            ORDER BY created_at DESC
        """, (uat.project, f"%{uat.version}%"), fetch="one")

        # Build content from actual UAT data
        content = f"# UAT Results for {uat.project} v{uat.version}\n\n"
        if uat.feature:
            content += f"**Feature**: {uat.feature}\n\n"
        content += f"**Status**: {uat.status.value}\n"
        content += f"**Tests**: {uat.passed} passed, {uat.failed} failed"
        if uat.skipped:
            content += f", {uat.skipped} skipped"
        content += f" (out of {uat.total_tests} total)\n\n"
        content += "---\n\n"
        content += uat.results_text

        if handoff:
            handoff_id = str(handoff['id'])
            logger.info(f"Found existing handoff {handoff_id} for {uat.project} {uat.version}")
            # Update existing handoff content with new UAT results
            execute_query("""
                UPDATE mcp_handoffs
                SET content = ?, updated_at = GETUTCDATE()
                WHERE id = ?
            """, (content, handoff_id), fetch="none")
        else:
            # Create a new handoff for this UAT submission (using pre-built content)
            result = execute_query("""
                INSERT INTO mcp_handoffs (
                    project, task, direction, status, content,
                    source, version, title
                )
                OUTPUT INSERTED.id
                VALUES (?, ?, 'ai_to_cc', 'pending_uat', ?, 'uat_checklist', ?, ?)
            """, (
                uat.project,
                task_id,
                content,
                uat.version,
                f"UAT: {uat.project} v{uat.version}"
            ), fetch="one")

            if not result:
                raise HTTPException(status_code=500, detail="Failed to create handoff")

            handoff_id = str(result['id'])
            logger.info(f"Created new handoff {handoff_id} for {uat.project} {uat.version}")

        # Insert UAT result
        uat_result = execute_query("""
            INSERT INTO uat_results (
                handoff_id, status, total_tests, passed, failed,
                notes_count, results_text, checklist_path
            )
            OUTPUT INSERTED.id, INSERTED.tested_at
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            handoff_id,
            uat.status.value,
            uat.total_tests,
            uat.passed,
            uat.failed,
            uat.notes_count or 0,
            uat.results_text,
            uat.checklist_path
        ), fetch="one")

        if not uat_result:
            raise HTTPException(status_code=500, detail="Failed to create UAT result")

        uat_id = str(uat_result['id'])

        # Update handoff status and UAT fields
        new_status = "done" if uat.status == UATStatus.PASSED else "needs_fixes"
        execute_query("""
            UPDATE mcp_handoffs
            SET status = ?,
                uat_status = ?,
                uat_passed = ?,
                uat_failed = ?,
                uat_date = GETUTCDATE(),
                updated_at = GETUTCDATE()
            WHERE id = ?
        """, (new_status, uat.status.value, uat.passed, uat.failed, handoff_id), fetch="none")

        handoff_url = f"https://metapm.rentyourcio.com/mcp/handoffs/{handoff_id}/content"

        return UATDirectSubmitResponse(
            handoff_id=handoff_id,
            uat_id=uat_id,
            status=uat.status.value,
            handoff_url=handoff_url,
            message=f"UAT results recorded for {uat.project} v{uat.version}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting direct UAT: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# UAT RETRIEVAL ENDPOINTS (Phase 5)
# ============================================

@router.get("/uat/latest", response_model=UATListItem)
async def get_latest_uat(
    project: Optional[str] = Query(None)
):
    """
    Get most recent UAT submission (PUBLIC - no auth).
    Optionally filter by project.
    """
    try:
        if project:
            result = execute_query("""
                SELECT TOP 1 u.id, u.handoff_id, u.status, u.total_tests,
                       u.passed, u.failed, u.notes_count, u.tested_by,
                       u.tested_at, u.results_text,
                       h.project, h.version
                FROM uat_results u
                JOIN mcp_handoffs h ON u.handoff_id = h.id
                WHERE h.project = ?
                ORDER BY u.tested_at DESC
            """, (project,), fetch="one")
        else:
            result = execute_query("""
                SELECT TOP 1 u.id, u.handoff_id, u.status, u.total_tests,
                       u.passed, u.failed, u.notes_count, u.tested_by,
                       u.tested_at, u.results_text,
                       h.project, h.version
                FROM uat_results u
                JOIN mcp_handoffs h ON u.handoff_id = h.id
                ORDER BY u.tested_at DESC
            """, fetch="one")

        if not result:
            raise HTTPException(status_code=404, detail="No UAT submissions found")

        return UATListItem(
            id=str(result['id']),
            handoff_id=str(result['handoff_id']),
            project=result.get('project'),
            version=result.get('version'),
            status=UATStatus(result['status']),
            total_tests=result['total_tests'],
            passed=result['passed'],
            failed=result['failed'],
            notes_count=result.get('notes_count'),
            tested_by=result.get('tested_by'),
            tested_at=result['tested_at'],
            results_text=result.get('results_text')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest UAT: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uat/list", response_model=UATListResponse)
async def list_uat_results(
    project: Optional[str] = Query(None),
    status: Optional[UATStatus] = Query(None),
    limit: int = Query(10, le=100),
    offset: int = Query(0)
):
    """
    List UAT submissions with optional filters (PUBLIC - no auth).
    """
    try:
        where_clauses = []
        params = []

        if project:
            where_clauses.append("h.project = ?")
            params.append(project)
        if status:
            where_clauses.append("u.status = ?")
            params.append(status.value)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_result = execute_query(
            f"""SELECT COUNT(*) as total
                FROM uat_results u
                JOIN mcp_handoffs h ON u.handoff_id = h.id
                WHERE {where_sql}""",
            tuple(params) if params else None,
            fetch="one"
        )
        total = count_result['total'] if count_result else 0

        # Get paginated results
        params.extend([offset, limit])
        results = execute_query(f"""
            SELECT u.id, u.handoff_id, u.status, u.total_tests,
                   u.passed, u.failed, u.notes_count, u.tested_by,
                   u.tested_at, u.results_text,
                   h.project, h.version
            FROM uat_results u
            JOIN mcp_handoffs h ON u.handoff_id = h.id
            WHERE {where_sql}
            ORDER BY u.tested_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, tuple(params), fetch="all")

        items = []
        for row in (results or []):
            items.append(UATListItem(
                id=str(row['id']),
                handoff_id=str(row['handoff_id']),
                project=row.get('project'),
                version=row.get('version'),
                status=UATStatus(row['status']),
                total_tests=row['total_tests'],
                passed=row['passed'],
                failed=row['failed'],
                notes_count=row.get('notes_count'),
                tested_by=row.get('tested_by'),
                tested_at=row['tested_at'],
                results_text=row.get('results_text')
            ))

        return UATListResponse(results=items, total=total)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing UAT results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uat/{uat_id}", response_model=UATListItem)
async def get_uat_by_id(uat_id: str):
    """
    Get a specific UAT result by its ID (PUBLIC - no auth).
    """
    try:
        result = execute_query("""
            SELECT u.id, u.handoff_id, u.status, u.total_tests,
                   u.passed, u.failed, u.notes_count, u.tested_by,
                   u.tested_at, u.results_text,
                   h.project, h.version
            FROM uat_results u
            JOIN mcp_handoffs h ON u.handoff_id = h.id
            WHERE u.id = ?
        """, (uat_id,), fetch="one")

        if not result:
            raise HTTPException(status_code=404, detail="UAT result not found")

        return UATListItem(
            id=str(result['id']),
            handoff_id=str(result['handoff_id']),
            project=result.get('project'),
            version=result.get('version'),
            status=UATStatus(result['status']),
            total_tests=result['total_tests'],
            passed=result['passed'],
            failed=result['failed'],
            notes_count=result.get('notes_count'),
            tested_by=result.get('tested_by'),
            tested_at=result['tested_at'],
            results_text=result.get('results_text')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting UAT result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HANDOFF DETAIL ENDPOINTS (wildcard routes must come after specific routes)
# ============================================

@router.get("/handoffs/{handoff_id}", response_model=HandoffResponse)
async def get_handoff(
    handoff_id: str,
    _: bool = Depends(verify_api_key)
):
    """Get a single handoff by ID (authenticated)."""
    try:
        result = execute_query("""
            SELECT id, project, task, direction, status, content, metadata, response_to, created_at, updated_at
            FROM mcp_handoffs
            WHERE id = ?
        """, (handoff_id,), fetch="one")

        if not result:
            raise HTTPException(status_code=404, detail="Handoff not found")

        public_url = f"https://metapm.rentyourcio.com/mcp/handoffs/{result['id']}/content"

        return HandoffResponse(
            id=str(result['id']),
            project=result['project'],
            task=result['task'],
            direction=HandoffDirection(result['direction']),
            status=HandoffStatus(result['status']),
            content=result['content'],
            metadata=_parse_json_field(result['metadata']),
            response_to=str(result['response_to']) if result['response_to'] else None,
            public_url=public_url,
            created_at=result['created_at'],
            updated_at=result['updated_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting handoff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/handoffs/{handoff_id}/content")
async def get_handoff_content(handoff_id: str):
    """
    Get handoff content (PUBLIC - no auth required).
    Returns raw markdown for Claude.ai's web_fetch.
    """
    try:
        result = execute_query("""
            SELECT content FROM mcp_handoffs WHERE id = ?
        """, (handoff_id,), fetch="one")

        if not result:
            raise HTTPException(status_code=404, detail="Handoff not found")

        return Response(
            content=result['content'],
            media_type="text/markdown"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting handoff content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/handoffs/{handoff_id}", response_model=HandoffResponse)
async def update_handoff(
    handoff_id: str,
    update: HandoffUpdate,
    _: bool = Depends(verify_api_key)
):
    """Update handoff status."""
    try:
        if update.status:
            execute_query("""
                UPDATE mcp_handoffs
                SET status = ?, updated_at = GETUTCDATE()
                WHERE id = ?
            """, (update.status.value, handoff_id), fetch="none")

        # Return updated handoff
        return await get_handoff(handoff_id, _)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating handoff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# TASK ENDPOINTS
# ============================================

@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    _: bool = Depends(verify_api_key)
):
    """Create a new MCP task."""
    try:
        tags_json = json.dumps(task.tags) if task.tags else None

        result = execute_query("""
            INSERT INTO mcp_tasks (project, title, description, priority, assigned_to,
                                   related_handoff_id, tags, notes, due_date)
            OUTPUT INSERTED.id, INSERTED.project, INSERTED.title, INSERTED.description,
                   INSERTED.priority, INSERTED.status, INSERTED.assigned_to,
                   INSERTED.related_handoff_id, INSERTED.tags, INSERTED.notes,
                   INSERTED.due_date, INSERTED.created_at, INSERTED.updated_at, INSERTED.completed_at
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.project,
            task.title,
            task.description,
            task.priority.value,
            task.assigned_to.value if task.assigned_to else None,
            task.related_handoff_id,
            tags_json,
            task.notes,
            task.due_date
        ), fetch="one")

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create task")

        return TaskResponse(
            id=str(result['id']),
            project=result['project'],
            title=result['title'],
            description=result['description'],
            priority=TaskPriority(result['priority']),
            status=TaskStatus(result['status']),
            assigned_to=result['assigned_to'],
            related_handoff_id=str(result['related_handoff_id']) if result['related_handoff_id'] else None,
            tags=_parse_tags_field(result['tags']),
            notes=result['notes'],
            due_date=result['due_date'],
            created_at=result['created_at'],
            updated_at=result['updated_at'],
            completed_at=result['completed_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    project: Optional[str] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    assigned_to: Optional[str] = Query(None),
    priority: Optional[TaskPriority] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    _: bool = Depends(verify_api_key)
):
    """List MCP tasks with optional filters."""
    try:
        where_clauses = []
        params = []

        if project:
            where_clauses.append("project = ?")
            params.append(project)
        if status:
            where_clauses.append("status = ?")
            params.append(status.value)
        if assigned_to:
            where_clauses.append("assigned_to = ?")
            params.append(assigned_to)
        if priority:
            where_clauses.append("priority = ?")
            params.append(priority.value)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_result = execute_query(
            f"SELECT COUNT(*) as total FROM mcp_tasks WHERE {where_sql}",
            tuple(params) if params else None,
            fetch="one"
        )
        total = count_result['total'] if count_result else 0

        # Get paginated results
        params.extend([offset, limit])
        results = execute_query(f"""
            SELECT id, project, title, description, priority, status, assigned_to,
                   related_handoff_id, tags, notes, due_date, created_at, updated_at, completed_at
            FROM mcp_tasks
            WHERE {where_sql}
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END,
                created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, tuple(params), fetch="all")

        tasks = []
        for row in (results or []):
            tasks.append(TaskResponse(
                id=str(row['id']),
                project=row['project'],
                title=row['title'],
                description=row['description'],
                priority=TaskPriority(row['priority']),
                status=TaskStatus(row['status']),
                assigned_to=row['assigned_to'],
                related_handoff_id=str(row['related_handoff_id']) if row['related_handoff_id'] else None,
                tags=_parse_tags_field(row['tags']),
                notes=row['notes'],
                due_date=row['due_date'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                completed_at=row['completed_at']
            ))

        return TaskListResponse(
            tasks=tasks,
            total=total,
            has_more=(offset + limit) < total
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    _: bool = Depends(verify_api_key)
):
    """Get a single task by ID."""
    try:
        result = execute_query("""
            SELECT id, project, title, description, priority, status, assigned_to,
                   related_handoff_id, tags, notes, due_date, created_at, updated_at, completed_at
            FROM mcp_tasks
            WHERE id = ?
        """, (task_id,), fetch="one")

        if not result:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskResponse(
            id=str(result['id']),
            project=result['project'],
            title=result['title'],
            description=result['description'],
            priority=TaskPriority(result['priority']),
            status=TaskStatus(result['status']),
            assigned_to=result['assigned_to'],
            related_handoff_id=str(result['related_handoff_id']) if result['related_handoff_id'] else None,
            tags=_parse_tags_field(result['tags']),
            notes=result['notes'],
            due_date=result['due_date'],
            created_at=result['created_at'],
            updated_at=result['updated_at'],
            completed_at=result['completed_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    update: TaskUpdate,
    _: bool = Depends(verify_api_key)
):
    """Update a task."""
    try:
        # Build dynamic update
        set_clauses = ["updated_at = GETUTCDATE()"]
        params = []

        if update.title is not None:
            set_clauses.append("title = ?")
            params.append(update.title)
        if update.description is not None:
            set_clauses.append("description = ?")
            params.append(update.description)
        if update.priority is not None:
            set_clauses.append("priority = ?")
            params.append(update.priority.value)
        if update.status is not None:
            set_clauses.append("status = ?")
            params.append(update.status.value)
            if update.status == TaskStatus.DONE:
                set_clauses.append("completed_at = GETUTCDATE()")
        if update.assigned_to is not None:
            set_clauses.append("assigned_to = ?")
            params.append(update.assigned_to.value)
        if update.tags is not None:
            set_clauses.append("tags = ?")
            params.append(json.dumps(update.tags))
        if update.notes is not None:
            set_clauses.append("notes = ?")
            params.append(update.notes)
        if update.due_date is not None:
            set_clauses.append("due_date = ?")
            params.append(update.due_date)

        params.append(task_id)

        execute_query(f"""
            UPDATE mcp_tasks
            SET {", ".join(set_clauses)}
            WHERE id = ?
        """, tuple(params), fetch="none")

        return await get_task(task_id, _)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    _: bool = Depends(verify_api_key)
):
    """Delete a task."""
    try:
        result = execute_query(
            "DELETE FROM mcp_tasks WHERE id = ?",
            (task_id,),
            fetch="none"
        )
        return Response(status_code=204)
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LOG ENDPOINT
# ============================================

@router.get("/log", response_model=LogResponse)
async def get_activity_log(
    project: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    _: bool = Depends(verify_api_key)
):
    """Get activity log combining handoffs and tasks."""
    try:
        where_clause = f"WHERE project = ?" if project else ""
        params = [project] if project else []

        # Get recent handoffs
        handoffs = execute_query(f"""
            SELECT id, created_at, project, task, direction
            FROM mcp_handoffs
            {where_clause}
            ORDER BY created_at DESC
        """, tuple(params) if params else None, fetch="all") or []

        # Get recent tasks
        tasks = execute_query(f"""
            SELECT id, created_at, project, title, status
            FROM mcp_tasks
            {where_clause}
            ORDER BY created_at DESC
        """, tuple(params) if params else None, fetch="all") or []

        # Combine and sort
        entries = []

        for h in handoffs:
            direction_label = "CC → AI" if h['direction'] == 'cc_to_ai' else "AI → CC"
            entries.append(LogEntry(
                timestamp=h['created_at'],
                type=LogEntryType.HANDOFF,
                project=h['project'],
                summary=f"{direction_label}: {h['task']}",
                id=str(h['id'])
            ))

        for t in tasks:
            entries.append(LogEntry(
                timestamp=t['created_at'],
                type=LogEntryType.TASK,
                project=t['project'],
                summary=f"Task: {t['title']} ({t['status']})",
                id=str(t['id'])
            ))

        # Sort by timestamp descending and limit
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        entries = entries[:limit]

        return LogResponse(entries=entries)
    except Exception as e:
        logger.error(f"Error getting activity log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HEALTH ENDPOINT
# ============================================

@router.get("/health")
async def mcp_health():
    """MCP-specific health check."""
    return {
        "status": "healthy",
        "service": "mcp",
        "version": settings.VERSION,
        "api_key_configured": bool(settings.MCP_API_KEY)
    }

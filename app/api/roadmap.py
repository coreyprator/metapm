"""
MetaPM Roadmap API Router
Project, Requirement, and Sprint management endpoints.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import PlainTextResponse

from app.core.database import execute_query
from app.schemas.roadmap import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    SprintCreate, SprintUpdate, SprintResponse, SprintListResponse,
    RequirementCreate, RequirementUpdate, RequirementResponse, RequirementListResponse,
    ProjectRoadmapItem, RoadmapResponse,
    ProjectStatus, RequirementStatus, RequirementType, RequirementPriority, SprintStatus,
    CategoryResponse, CategoryCreate,
    RoadmapTaskCreate, RoadmapTaskUpdate, RoadmapTaskResponse,
    TestPlanCreate, TestPlanResponse, TestCaseCreate, TestCaseResponse, TestCaseUpdate,
    DependencyCreate, DependencyResponse,
    StatusTransitionRequest, StatusTransitionResponse, BatchStatusRequest,
    RequirementHistoryResponse, HistoryEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _project_done_counts() -> dict:
    rows = execute_query("""
        SELECT project_id,
               COUNT(*) as total_count,
               SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as done_count
        FROM roadmap_requirements
        GROUP BY project_id
    """, fetch="all") or []
    return {
        row['project_id']: {
            'total': int(row.get('total_count') or 0),
            'done': int(row.get('done_count') or 0),
        }
        for row in rows
    }


# ============================================
# PROJECT ENDPOINTS
# ============================================

@router.get("/projects", response_model=ProjectListResponse)
@router.get("/roadmap/projects", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[ProjectStatus] = Query(None),
    limit: int = Query(20, le=500),
    offset: int = Query(0)
):
    """List all projects with optional status filter."""
    try:
        where_clause = "WHERE status = ?" if status else ""
        params = [status.value] if status else []

        # Get count
        count_result = execute_query(
            f"SELECT COUNT(*) as total FROM roadmap_projects {where_clause}",
            tuple(params) if params else None,
            fetch="one"
        )
        total = count_result['total'] if count_result else 0

        # Get projects
        params.extend([offset, limit])
        results = execute_query(f"""
            SELECT p.id, p.code, p.name, p.emoji, p.color, p.current_version, p.status,
                   p.repo_url, p.deploy_url, p.category_id, p.created_at, p.updated_at,
                   c.name as category_name
            FROM roadmap_projects p
            LEFT JOIN roadmap_categories c ON p.category_id = c.id
            {where_clause}
            ORDER BY p.name
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, tuple(params), fetch="all")

        projects = []
        for row in (results or []):
            projects.append(ProjectResponse(
                id=row['id'],
                code=row['code'],
                name=row['name'],
                emoji=row['emoji'],
                color=row['color'],
                current_version=row['current_version'],
                status=ProjectStatus(row['status']) if row['status'] else ProjectStatus.ACTIVE,
                repo_url=row['repo_url'],
                deploy_url=row['deploy_url'],
                category_id=row.get('category_id'),
                category_name=row.get('category_name'),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))

        return ProjectListResponse(projects=projects, total=total)
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectResponse)
@router.get("/roadmap/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a single project by ID."""
    try:
        result = execute_query("""
            SELECT p.id, p.code, p.name, p.emoji, p.color, p.current_version, p.status,
                   p.repo_url, p.deploy_url, p.category_id, p.created_at, p.updated_at,
                   c.name as category_name
            FROM roadmap_projects p
            LEFT JOIN roadmap_categories c ON p.category_id = c.id
            WHERE p.id = ?
        """, (project_id,), fetch="one")

        if not result:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectResponse(
            id=result['id'],
            code=result['code'],
            name=result['name'],
            emoji=result['emoji'],
            color=result['color'],
            current_version=result['current_version'],
            status=ProjectStatus(result['status']) if result['status'] else ProjectStatus.ACTIVE,
            repo_url=result['repo_url'],
            deploy_url=result['deploy_url'],
            category_id=result.get('category_id'),
            category_name=result.get('category_name'),
            created_at=result['created_at'],
            updated_at=result['updated_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects", response_model=ProjectResponse, status_code=201)
@router.post("/roadmap/projects", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate):
    """Create a new project."""
    try:
        execute_query("""
            INSERT INTO roadmap_projects (id, code, name, emoji, color, current_version, status, repo_url, deploy_url, category_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project.id, project.code, project.name, project.emoji, project.color,
            project.current_version, project.status.value, project.repo_url, project.deploy_url,
            project.category_id
        ), fetch="none")

        return await get_project(project.id)
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}", response_model=ProjectResponse)
@router.put("/roadmap/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, update: ProjectUpdate):
    """Update a project."""
    try:
        set_clauses = ["updated_at = GETDATE()"]
        params = []

        if update.name is not None:
            set_clauses.append("name = ?")
            params.append(update.name)
        if update.emoji is not None:
            set_clauses.append("emoji = ?")
            params.append(update.emoji)
        if update.color is not None:
            set_clauses.append("color = ?")
            params.append(update.color)
        if update.current_version is not None:
            set_clauses.append("current_version = ?")
            params.append(update.current_version)
        if update.status is not None:
            set_clauses.append("status = ?")
            params.append(update.status.value)
        if update.repo_url is not None:
            set_clauses.append("repo_url = ?")
            params.append(update.repo_url)
        if update.deploy_url is not None:
            set_clauses.append("deploy_url = ?")
            params.append(update.deploy_url)
        if update.category_id is not None:
            set_clauses.append("category_id = ?")
            params.append(update.category_id if update.category_id else None)

        params.append(project_id)

        execute_query(f"""
            UPDATE roadmap_projects SET {", ".join(set_clauses)} WHERE id = ?
        """, tuple(params), fetch="none")

        return await get_project(project_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}", status_code=204)
@router.delete("/roadmap/projects/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """Delete a project only if it has no linked requirements."""
    try:
        project = execute_query(
            "SELECT id FROM roadmap_projects WHERE id = ?",
            (project_id,),
            fetch="one"
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        linked = execute_query(
            "SELECT COUNT(*) as cnt FROM roadmap_requirements WHERE project_id = ?",
            (project_id,),
            fetch="one"
        )
        linked_count = int((linked or {}).get('cnt') or 0)
        if linked_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete project with {linked_count} requirements. Delete requirements first."
            )

        execute_query("DELETE FROM roadmap_projects WHERE id = ?", (project_id,), fetch="none")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SPRINT ENDPOINTS
# ============================================

@router.get("/sprints", response_model=SprintListResponse)
@router.get("/roadmap/sprints", response_model=SprintListResponse)
async def list_sprints(
    project_id: Optional[str] = Query(None),
    status: Optional[SprintStatus] = Query(None),
    limit: int = Query(20, le=500),
    offset: int = Query(0)
):
    """List all sprints with optional status filter."""
    try:
        where_clauses = []
        params = []

        if project_id:
            where_clauses.append("project_id = ?")
            params.append(project_id)
        if status:
            where_clauses.append("status = ?")
            params.append(status.value)

        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_result = execute_query(
            f"SELECT COUNT(*) as total FROM roadmap_sprints {where_clause}",
            tuple(params) if params else None,
            fetch="one"
        )
        total = count_result['total'] if count_result else 0

        params.extend([offset, limit])
        results = execute_query(f"""
            SELECT id, project_id, name, description, status, start_date, end_date, created_at
            FROM roadmap_sprints
            {where_clause}
            ORDER BY start_date DESC, created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, tuple(params), fetch="all")

        sprints = []
        for row in (results or []):
            sprints.append(SprintResponse(
                id=row['id'],
                project_id=row.get('project_id'),
                name=row['name'],
                description=row['description'],
                status=SprintStatus(row['status']) if row['status'] else SprintStatus.PLANNED,
                start_date=row['start_date'],
                end_date=row['end_date'],
                created_at=row['created_at']
            ))

        return SprintListResponse(sprints=sprints, total=total)
    except Exception as e:
        logger.error(f"Error listing sprints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sprints/{sprint_id}", response_model=SprintResponse)
@router.get("/roadmap/sprints/{sprint_id}", response_model=SprintResponse)
async def get_sprint(sprint_id: str):
    """Get a single sprint by ID."""
    try:
        result = execute_query("""
            SELECT id, project_id, name, description, status, start_date, end_date, created_at
            FROM roadmap_sprints WHERE id = ?
        """, (sprint_id,), fetch="one")

        if not result:
            raise HTTPException(status_code=404, detail="Sprint not found")

        return SprintResponse(
            id=result['id'],
            project_id=result.get('project_id'),
            name=result['name'],
            description=result['description'],
            status=SprintStatus(result['status']) if result['status'] else SprintStatus.PLANNED,
            start_date=result['start_date'],
            end_date=result['end_date'],
            created_at=result['created_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sprints", response_model=SprintResponse, status_code=201)
@router.post("/roadmap/sprints", response_model=SprintResponse, status_code=201)
async def create_sprint(sprint: SprintCreate):
    """Create a new sprint."""
    try:
        execute_query("""
            INSERT INTO roadmap_sprints (id, project_id, name, description, status, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            sprint.id, sprint.project_id, sprint.name, sprint.description, sprint.status.value,
            sprint.start_date, sprint.end_date
        ), fetch="none")

        return await get_sprint(sprint.id)
    except Exception as e:
        logger.error(f"Error creating sprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sprints/{sprint_id}", response_model=SprintResponse)
@router.put("/roadmap/sprints/{sprint_id}", response_model=SprintResponse)
async def update_sprint(sprint_id: str, update: SprintUpdate):
    """Update a sprint."""
    try:
        set_clauses = []
        params = []

        if update.name is not None:
            set_clauses.append("name = ?")
            params.append(update.name)
        if update.description is not None:
            set_clauses.append("description = ?")
            params.append(update.description)
        if update.status is not None:
            set_clauses.append("status = ?")
            params.append(update.status.value)
        if update.start_date is not None:
            set_clauses.append("start_date = ?")
            params.append(update.start_date)
        if update.end_date is not None:
            set_clauses.append("end_date = ?")
            params.append(update.end_date)

        if set_clauses:
            params.append(sprint_id)
            execute_query(f"""
                UPDATE roadmap_sprints SET {", ".join(set_clauses)} WHERE id = ?
            """, tuple(params), fetch="none")

        return await get_sprint(sprint_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating sprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sprints/{sprint_id}", status_code=204)
@router.delete("/roadmap/sprints/{sprint_id}", status_code=204)
async def delete_sprint(sprint_id: str):
    """Delete a sprint and unassign linked requirements first."""
    try:
        sprint = execute_query(
            "SELECT id FROM roadmap_sprints WHERE id = ?",
            (sprint_id,),
            fetch="one"
        )
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")

        execute_query(
            "UPDATE roadmap_requirements SET sprint_id = NULL, updated_at = GETDATE() WHERE sprint_id = ?",
            (sprint_id,),
            fetch="none"
        )
        execute_query("DELETE FROM roadmap_sprints WHERE id = ?", (sprint_id,), fetch="none")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting sprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# REQUIREMENT ENDPOINTS
# ============================================

@router.get("/requirements", response_model=RequirementListResponse)
@router.get("/roadmap/requirements", response_model=RequirementListResponse)
async def list_requirements(
    project_id: Optional[str] = Query(None),
    project_code: Optional[str] = Query(None),
    status: Optional[RequirementStatus] = Query(None),
    type: Optional[RequirementType] = Query(None),
    priority: Optional[RequirementPriority] = Query(None),
    sprint_id: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0)
):
    """List requirements with filters."""
    try:
        where_clauses = []
        params = []

        if project_id:
            where_clauses.append("r.project_id = ?")
            params.append(project_id)
        if project_code:
            where_clauses.append("p.code = ?")
            params.append(project_code)
        if status:
            where_clauses.append("r.status = ?")
            params.append(status.value)
        if type:
            where_clauses.append("r.type = ?")
            params.append(type.value)
        if priority:
            where_clauses.append("r.priority = ?")
            params.append(priority.value)
        if sprint_id:
            where_clauses.append("r.sprint_id = ?")
            params.append(sprint_id)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        count_result = execute_query(f"""
            SELECT COUNT(*) as total FROM roadmap_requirements r
            JOIN roadmap_projects p ON r.project_id = p.id
            WHERE {where_sql}
        """, tuple(params) if params else None, fetch="one")
        total = count_result['total'] if count_result else 0

        params.extend([offset, limit])
        results = execute_query(f"""
            SELECT r.id, r.project_id, r.code, r.title, r.description,
                   r.type, r.priority, r.status, r.target_version,
                   r.sprint_id, r.handoff_id, r.uat_id,
                   r.created_at, r.updated_at,
                   p.code as project_code, p.name as project_name, p.emoji as project_emoji
            FROM roadmap_requirements r
            JOIN roadmap_projects p ON r.project_id = p.id
            WHERE {where_sql}
            ORDER BY
                CASE r.priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 END,
                r.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, tuple(params), fetch="all")

        requirements = []
        for row in (results or []):
            requirements.append(RequirementResponse(
                id=row['id'],
                project_id=row['project_id'],
                code=row['code'],
                title=row['title'],
                description=row['description'],
                type=RequirementType(row['type']) if row['type'] else RequirementType.TASK,
                priority=RequirementPriority(row['priority']) if row['priority'] else RequirementPriority.P2,
                status=RequirementStatus(row['status']) if row['status'] else RequirementStatus.BACKLOG,
                target_version=row['target_version'],
                sprint_id=row['sprint_id'],
                handoff_id=str(row['handoff_id']) if row['handoff_id'] else None,
                uat_id=str(row['uat_id']) if row['uat_id'] else None,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                project_code=row['project_code'],
                project_name=row['project_name'],
                project_emoji=row['project_emoji']
            ))

        return RequirementListResponse(requirements=requirements, total=total)
    except Exception as e:
        logger.error(f"Error listing requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requirements/{requirement_id}", response_model=RequirementResponse)
@router.get("/roadmap/requirements/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(requirement_id: str):
    """Get a single requirement by ID."""
    try:
        result = execute_query("""
            SELECT r.id, r.project_id, r.code, r.title, r.description,
                   r.type, r.priority, r.status, r.target_version,
                   r.sprint_id, r.handoff_id, r.uat_id,
                   r.created_at, r.updated_at,
                   p.code as project_code, p.name as project_name, p.emoji as project_emoji
            FROM roadmap_requirements r
            JOIN roadmap_projects p ON r.project_id = p.id
            WHERE r.id = ?
        """, (requirement_id,), fetch="one")

        if not result:
            raise HTTPException(status_code=404, detail="Requirement not found")

        return RequirementResponse(
            id=result['id'],
            project_id=result['project_id'],
            code=result['code'],
            title=result['title'],
            description=result['description'],
            type=RequirementType(result['type']) if result['type'] else RequirementType.TASK,
            priority=RequirementPriority(result['priority']) if result['priority'] else RequirementPriority.P2,
            status=RequirementStatus(result['status']) if result['status'] else RequirementStatus.BACKLOG,
            target_version=result['target_version'],
            sprint_id=result['sprint_id'],
            handoff_id=str(result['handoff_id']) if result['handoff_id'] else None,
            uat_id=str(result['uat_id']) if result['uat_id'] else None,
            created_at=result['created_at'],
            updated_at=result['updated_at'],
            project_code=result['project_code'],
            project_name=result['project_name'],
            project_emoji=result['project_emoji']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting requirement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/requirements", response_model=RequirementResponse, status_code=201)
@router.post("/roadmap/requirements", response_model=RequirementResponse, status_code=201)
async def create_requirement(req: RequirementCreate):
    """Create a new requirement."""
    try:
        execute_query("""
            INSERT INTO roadmap_requirements (id, project_id, code, title, description, type, priority, status, target_version, sprint_id, handoff_id, uat_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req.id, req.project_id, req.code, req.title, req.description,
            req.type.value, req.priority.value, req.status.value, req.target_version,
            req.sprint_id, req.handoff_id, req.uat_id
        ), fetch="none")

        return await get_requirement(req.id)
    except Exception as e:
        logger.error(f"Error creating requirement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/requirements/{requirement_id}", response_model=RequirementResponse)
@router.put("/roadmap/requirements/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(requirement_id: str, update: RequirementUpdate):
    """Update a requirement."""
    try:
        set_clauses = ["updated_at = GETDATE()"]
        params = []

        if update.code is not None:
            # Validate code uniqueness within the same project
            existing = execute_query("""
                SELECT id FROM roadmap_requirements
                WHERE project_id = (SELECT project_id FROM roadmap_requirements WHERE id = ?)
                  AND code = ? AND id != ?
            """, (requirement_id, update.code, requirement_id), fetch="one")
            if existing:
                raise HTTPException(status_code=409, detail=f"Code '{update.code}' already exists in this project")
            set_clauses.append("code = ?")
            params.append(update.code)
        if update.title is not None:
            set_clauses.append("title = ?")
            params.append(update.title)
        if update.description is not None:
            set_clauses.append("description = ?")
            params.append(update.description)
        if update.type is not None:
            set_clauses.append("type = ?")
            params.append(update.type.value)
        if update.priority is not None:
            set_clauses.append("priority = ?")
            params.append(update.priority.value)
        if update.status is not None:
            set_clauses.append("status = ?")
            params.append(update.status.value)
        if update.target_version is not None:
            set_clauses.append("target_version = ?")
            params.append(update.target_version)
        if update.sprint_id is not None:
            set_clauses.append("sprint_id = ?")
            params.append(update.sprint_id)
        if update.handoff_id is not None:
            set_clauses.append("handoff_id = ?")
            params.append(update.handoff_id)
        if update.uat_id is not None:
            set_clauses.append("uat_id = ?")
            params.append(update.uat_id)

        params.append(requirement_id)

        execute_query(f"""
            UPDATE roadmap_requirements SET {", ".join(set_clauses)} WHERE id = ?
        """, tuple(params), fetch="none")

        return await get_requirement(requirement_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating requirement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/next-code/{project_code}/{item_type}")
async def get_next_roadmap_code(project_code: str, item_type: str):
    """Get next sequential code for a type within a project. Returns e.g. BUG-004."""
    try:
        prefix_map = {
            'feature': 'REQ', 'requirement': 'REQ', 'enhancement': 'REQ',
            'bug': 'BUG', 'task': 'TSK', 'uat': 'UAT', 'sprint': 'SPR'
        }
        prefix = prefix_map.get(item_type.lower(), 'REQ')

        result = execute_query("""
            SELECT MAX(
                TRY_CAST(
                    SUBSTRING(r.code, CHARINDEX('-', r.code) + 1, LEN(r.code)) AS INT
                )
            ) as maxNum
            FROM roadmap_requirements r
            JOIN roadmap_projects p ON r.project_id = p.id
            WHERE p.code = ? AND r.code LIKE ?
        """, (project_code, f"{prefix}-%"), fetch="one")

        next_num = (result['maxNum'] or 0) + 1 if result else 1
        return {"code": f"{prefix}-{next_num:03d}", "prefix": prefix, "number": next_num}
    except Exception as e:
        logger.error(f"Error getting next code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/requirements/{requirement_id}", status_code=204)
@router.delete("/roadmap/requirements/{requirement_id}", status_code=204)
async def delete_requirement(requirement_id: str):
    """Delete a requirement."""
    try:
        execute_query("DELETE FROM roadmap_requirements WHERE id = ?", (requirement_id,), fetch="none")
    except Exception as e:
        logger.error(f"Error deleting requirement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requirements/{requirement_id}/handoffs")
@router.get("/roadmap/requirements/{requirement_id}/handoffs")
async def list_requirement_handoffs(requirement_id: str):
    """List linked MCP handoffs for a requirement."""
    try:
        req = execute_query(
            "SELECT id, code FROM roadmap_requirements WHERE id = ?",
            (requirement_id,),
            fetch="one"
        )
        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")

        results = execute_query("""
            SELECT h.id, h.project, h.task, h.status, h.direction, h.created_at
            FROM roadmap_requirement_handoffs rrh
            JOIN mcp_handoffs h ON rrh.handoff_id = h.id
            WHERE rrh.requirement_id = ?
            ORDER BY h.created_at DESC
        """, (requirement_id,), fetch="all") or []

        return {
            "requirement_id": requirement_id,
            "requirement_code": req['code'],
            "handoffs": [
                {
                    "id": str(row['id']),
                    "project": row.get('project'),
                    "task": row.get('task'),
                    "status": row.get('status'),
                    "direction": row.get('direction'),
                    "created_at": row['created_at'].isoformat() if row.get('created_at') else None,
                    "url": f"https://metapm.rentyourcio.com/mcp/handoffs/{row['id']}/content"
                }
                for row in results
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing requirement handoffs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ROADMAP AGGREGATE ENDPOINT
# ============================================

@router.get("/roadmap", response_model=RoadmapResponse)
async def get_roadmap(
    project_code: Optional[str] = Query(None)
):
    """Get aggregated roadmap view for dashboard."""
    try:
        # Get projects (show all active and stable, exclude paused/archived)
        if project_code:
            project_where = "WHERE code = ?"
            project_params = (project_code,)
        else:
            project_where = "WHERE status IN ('active', 'stable')"
            project_params = None

        projects_result = execute_query(f"""
            SELECT id, code, name, emoji, color, current_version, status
            FROM roadmap_projects
            {project_where}
            ORDER BY name
        """, project_params, fetch="all")

        roadmap_items = []

        for proj in (projects_result or []):
            # Get requirements for this project
            reqs_result = execute_query("""
                SELECT r.id, r.project_id, r.code, r.title, r.description,
                       r.type, r.priority, r.status, r.target_version,
                       r.sprint_id, r.handoff_id, r.uat_id,
                       r.created_at, r.updated_at,
                       p.code as project_code, p.name as project_name, p.emoji as project_emoji
                FROM roadmap_requirements r
                JOIN roadmap_projects p ON r.project_id = p.id
                WHERE r.project_id = ?
                ORDER BY
                    CASE r.priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 END,
                    CASE r.status
                        WHEN 'executing' THEN 1
                        WHEN 'handoff' THEN 2
                        WHEN 'uat' THEN 3
                        WHEN 'needs_fixes' THEN 4
                        WHEN 'approved' THEN 5
                        WHEN 'prompt_ready' THEN 6
                        WHEN 'draft' THEN 7
                        WHEN 'backlog' THEN 8
                        WHEN 'closed' THEN 9
                        WHEN 'deferred' THEN 10
                    END
            """, (proj['id'],), fetch="all")

            requirements = []
            for row in (reqs_result or []):
                requirements.append(RequirementResponse(
                    id=row['id'],
                    project_id=row['project_id'],
                    code=row['code'],
                    title=row['title'],
                    description=row['description'],
                    type=RequirementType(row['type']) if row['type'] else RequirementType.TASK,
                    priority=RequirementPriority(row['priority']) if row['priority'] else RequirementPriority.P2,
                    status=RequirementStatus(row['status']) if row['status'] else RequirementStatus.BACKLOG,
                    target_version=row['target_version'],
                    sprint_id=row['sprint_id'],
                    handoff_id=str(row['handoff_id']) if row['handoff_id'] else None,
                    uat_id=str(row['uat_id']) if row['uat_id'] else None,
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    project_code=row['project_code'],
                    project_name=row['project_name'],
                    project_emoji=row['project_emoji']
                ))

            roadmap_items.append(ProjectRoadmapItem(
                project_id=proj['id'],
                project_code=proj['code'],
                project_name=proj['name'],
                project_emoji=proj['emoji'] or '',
                current_version=proj['current_version'],
                requirements=requirements
            ))

        # Calculate stats
        stats_result = execute_query("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'backlog' THEN 1 ELSE 0 END) as backlog,
                SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft,
                SUM(CASE WHEN status = 'prompt_ready' THEN 1 ELSE 0 END) as prompt_ready,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'executing' THEN 1 ELSE 0 END) as executing,
                SUM(CASE WHEN status = 'handoff' THEN 1 ELSE 0 END) as handoff,
                SUM(CASE WHEN status = 'uat' THEN 1 ELSE 0 END) as uat,
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN status = 'needs_fixes' THEN 1 ELSE 0 END) as needs_fixes,
                SUM(CASE WHEN status = 'deferred' THEN 1 ELSE 0 END) as deferred
            FROM roadmap_requirements
        """, fetch="one")

        stats = {
            "total": stats_result['total'] or 0,
            "backlog": stats_result['backlog'] or 0,
            "draft": stats_result['draft'] or 0,
            "prompt_ready": stats_result['prompt_ready'] or 0,
            "approved": stats_result['approved'] or 0,
            "executing": stats_result['executing'] or 0,
            "handoff": stats_result['handoff'] or 0,
            "uat": stats_result['uat'] or 0,
            "closed": stats_result['closed'] or 0,
            "needs_fixes": stats_result['needs_fixes'] or 0,
            "deferred": stats_result['deferred'] or 0
        } if stats_result else {}

        return RoadmapResponse(projects=roadmap_items, stats=stats)
    except Exception as e:
        logger.error(f"Error getting roadmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/export")
async def export_roadmap():
    """Export full roadmap with projects, requirements, sprints, and aggregate stats."""
    try:
        projects = execute_query("""
            SELECT id, code, name, emoji, status, current_version, deploy_url
            FROM roadmap_projects
            ORDER BY name
        """, fetch="all") or []

        sprints = execute_query("""
            SELECT id, project_id, name, description, status, start_date, end_date, created_at
            FROM roadmap_sprints
            ORDER BY created_at DESC
        """, fetch="all") or []

        requirements = execute_query("""
            SELECT id, project_id, code, title, description, type, priority, status,
                   target_version, sprint_id, created_at, updated_at
            FROM roadmap_requirements
            ORDER BY code
        """, fetch="all") or []

        sprint_by_id = {s['id']: s for s in sprints}
        counts_by_project = _project_done_counts()

        projects_out = []
        for p in projects:
            reqs_for_project = [r for r in requirements if r['project_id'] == p['id']]
            reqs_out = []
            for r in reqs_for_project:
                s = sprint_by_id.get(r.get('sprint_id')) if r.get('sprint_id') else None
                reqs_out.append({
                    "id": r['id'],
                    "code": r['code'],
                    "title": r['title'],
                    "description": r.get('description'),
                    "type": r.get('type'),
                    "priority": r.get('priority'),
                    "status": r.get('status'),
                    "target_version": r.get('target_version'),
                    "sprint_id": r.get('sprint_id'),
                    "sprint_name": s.get('name') if s else None,
                    "created_at": r.get('created_at'),
                    "updated_at": r.get('updated_at'),
                })

            counts = counts_by_project.get(p['id'], {'total': 0, 'done': 0})
            projects_out.append({
                "id": p['id'],
                "code": p.get('code'),
                "name": p.get('name'),
                "emoji": p.get('emoji'),
                "status": p.get('status'),
                "current_version": p.get('current_version'),
                "deploy_url": p.get('deploy_url'),
                "requirement_count": counts['total'],
                "done_count": counts['done'],
                "requirements": reqs_out,
            })

        stats_row = execute_query("""
            SELECT
                COUNT(*) as total_requirements,
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as done,
                SUM(CASE WHEN status = 'executing' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'backlog' THEN 1 ELSE 0 END) as backlog,
                SUM(CASE WHEN type = 'bug' THEN 1 ELSE 0 END) as bugs,
                SUM(CASE WHEN type = 'feature' THEN 1 ELSE 0 END) as features,
                SUM(CASE WHEN type = 'task' THEN 1 ELSE 0 END) as tasks
            FROM roadmap_requirements
        """, fetch="one") or {}

        return {
            "projects": projects_out,
            "stats": {
                "total_requirements": int(stats_row.get('total_requirements') or 0),
                "done": int(stats_row.get('done') or 0),
                "in_progress": int(stats_row.get('in_progress') or 0),
                "backlog": int(stats_row.get('backlog') or 0),
                "bugs": int(stats_row.get('bugs') or 0),
                "features": int(stats_row.get('features') or 0),
                "tasks": int(stats_row.get('tasks') or 0),
            },
            "sprints": [
                {
                    "id": s.get('id'),
                    "project_id": s.get('project_id'),
                    "name": s.get('name'),
                    "description": s.get('description'),
                    "status": s.get('status'),
                    "start_date": s.get('start_date'),
                    "end_date": s.get('end_date'),
                    "created_at": s.get('created_at'),
                }
                for s in sprints
            ],
        }
    except Exception as e:
        logger.error(f"Error exporting roadmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/seed")
async def seed_roadmap_data():
    """Seed initial project and requirement data (run once)."""
    try:
        # Check if projects exist
        existing = execute_query("SELECT COUNT(*) as cnt FROM roadmap_projects", fetch="one")
        if existing and existing['cnt'] > 0:
            return {"message": "Data already seeded", "projects": existing['cnt']}

        # Seed projects
        projects = [
            ('proj-hl', 'HL', 'HarmonyLab', '\U0001F535', '#3b82f6', '1.5.3', 'active'),
            ('proj-af', 'AF', 'ArtForge', '\U0001F7E0', '#f97316', '2.2.1', 'active'),
            ('proj-em', 'EM', 'Etymython', '\U0001F7E3', '#a855f7', '1.2.0', 'stable'),
            ('proj-sf', 'SF', 'Super-Flashcards', '\U0001F7E1', '#eab308', '8.0.0', 'stable'),
            ('proj-mp', 'MP', 'MetaPM', '\U0001F534', '#ef4444', '2.0.0', 'active'),
            ('proj-pm', 'PM', 'project-methodology', '\U0001F7E2', '#22c55e', '3.17.0', 'stable'),
        ]

        for p in projects:
            execute_query("""
                INSERT INTO roadmap_projects (id, code, name, emoji, color, current_version, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, p, fetch="none")

        # Seed requirements
        requirements = [
            # HarmonyLab
            ('req-hl-001', 'proj-hl', 'HL-001', 'Quiz backend fix', 'bug', 'P1', 'closed', '1.5.3'),
            ('req-hl-002', 'proj-hl', 'HL-002', 'Complete audio UAT', 'task', 'P1', 'uat', '1.5.3'),
            ('req-hl-003', 'proj-hl', 'HL-003', 'Show intervals on chord display', 'enhancement', 'P3', 'backlog', '1.6.0'),
            ('req-hl-004', 'proj-hl', 'HL-004', 'Progression quiz (next chord)', 'feature', 'P3', 'backlog', '1.6.0'),
            # ArtForge
            ('req-af-001', 'proj-af', 'AF-001', 'Export fixes (images + PDF)', 'bug', 'P1', 'planned', '2.2.2'),
            ('req-af-002', 'proj-af', 'AF-002', 'Voice selection for 11Labs', 'enhancement', 'P2', 'backlog', '2.2.2'),
            ('req-af-003', 'proj-af', 'AF-003', 'Slideshow feature (3 modes)', 'feature', 'P2', 'backlog', '2.3.0'),
            ('req-af-004', 'proj-af', 'AF-004', 'Runway Gen-3 video generation', 'feature', 'P2', 'backlog', '2.3.0'),
            # Etymython
            ('req-em-001', 'proj-em', 'EM-001', '11Labs VO from Origin Story', 'feature', 'P3', 'backlog', '2.0.0'),
            ('req-em-002', 'proj-em', 'EM-002', 'Link cognates SF<->EM', 'feature', 'P3', 'backlog', '2.0.0'),
            # Super Flashcards
            ('req-sf-001', 'proj-sf', 'SF-001', 'Performance stats per-user', 'bug', 'P3', 'backlog', '9.0.0'),
            ('req-sf-002', 'proj-sf', 'SF-002', 'IPA direction + silent letters', 'bug', 'P3', 'backlog', '9.0.0'),
            ('req-sf-003', 'proj-sf', 'SF-003', 'Related card hyperlinks', 'feature', 'P3', 'backlog', '9.0.0'),
            ('req-sf-004', 'proj-sf', 'SF-004', 'Back button navigation', 'feature', 'P3', 'backlog', '9.0.0'),
        ]

        for r in requirements:
            execute_query("""
                INSERT INTO roadmap_requirements (id, project_id, code, title, type, priority, status, target_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, r, fetch="none")

        return {"message": "Seed data created", "projects": len(projects), "requirements": len(requirements)}
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CATEGORY ENDPOINTS (MP-021)
# ============================================

@router.get("/roadmap/categories")
async def list_categories():
    """List all roadmap categories."""
    try:
        results = execute_query("""
            SELECT id, name, display_order, created_at
            FROM roadmap_categories
            ORDER BY display_order, name
        """, fetch="all") or []
        return {"categories": results, "total": len(results)}
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roadmap/categories", status_code=201)
async def create_category(cat: CategoryCreate):
    """Create a new roadmap category."""
    try:
        import uuid
        cat_id = f"cat-{cat.name.lower().replace(' ', '-')}"
        execute_query("""
            INSERT INTO roadmap_categories (id, name, display_order)
            VALUES (?, ?, ?)
        """, (cat_id, cat.name, cat.display_order), fetch="none")
        result = execute_query(
            "SELECT id, name, display_order, created_at FROM roadmap_categories WHERE id = ?",
            (cat_id,), fetch="one"
        )
        return result
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/roadmap/categories/{category_id}", status_code=204)
async def delete_category(category_id: str):
    """Delete a category if no projects reference it."""
    try:
        linked = execute_query(
            "SELECT COUNT(*) as cnt FROM roadmap_projects WHERE category_id = ?",
            (category_id,), fetch="one"
        )
        if linked and int(linked.get('cnt', 0)) > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete category with {linked['cnt']} linked projects."
            )
        execute_query("DELETE FROM roadmap_categories WHERE id = ?", (category_id,), fetch="none")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ROADMAP TASK ENDPOINTS (MP-012)
# ============================================

@router.get("/roadmap/tasks")
async def list_roadmap_tasks(
    requirement_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0)
):
    """List roadmap tasks, optionally filtered by requirement."""
    try:
        where_clauses = []
        params = []

        if requirement_id:
            where_clauses.append("t.requirement_id = ?")
            params.append(requirement_id)
        if status:
            where_clauses.append("t.status = ?")
            params.append(status)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        params.extend([offset, limit])
        results = execute_query(f"""
            SELECT t.id, t.requirement_id, t.title, t.description,
                   t.status, t.priority, t.assignee, t.created_at, t.updated_at
            FROM roadmap_tasks t
            WHERE {where_sql}
            ORDER BY
                CASE t.priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 END,
                t.created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, tuple(params), fetch="all") or []

        return {"tasks": results, "total": len(results)}
    except Exception as e:
        logger.error(f"Error listing roadmap tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roadmap/tasks", status_code=201)
async def create_roadmap_task(task: RoadmapTaskCreate):
    """Create a new roadmap task under a requirement."""
    try:
        import uuid
        task_id = task.id or str(uuid.uuid4())
        execute_query("""
            INSERT INTO roadmap_tasks (id, requirement_id, title, description, status, priority, assignee)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id, task.requirement_id, task.title, task.description,
            task.status.value, task.priority.value, task.assignee
        ), fetch="none")

        result = execute_query("""
            SELECT id, requirement_id, title, description, status, priority, assignee,
                   created_at, updated_at
            FROM roadmap_tasks WHERE id = ?
        """, (task_id,), fetch="one")
        return result
    except Exception as e:
        logger.error(f"Error creating roadmap task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/roadmap/tasks/{task_id}")
async def update_roadmap_task(task_id: str, update: RoadmapTaskUpdate):
    """Update a roadmap task."""
    try:
        set_clauses = ["updated_at = GETDATE()"]
        params = []

        if update.title is not None:
            set_clauses.append("title = ?")
            params.append(update.title)
        if update.description is not None:
            set_clauses.append("description = ?")
            params.append(update.description)
        if update.status is not None:
            set_clauses.append("status = ?")
            params.append(update.status.value)
        if update.priority is not None:
            set_clauses.append("priority = ?")
            params.append(update.priority.value)
        if update.assignee is not None:
            set_clauses.append("assignee = ?")
            params.append(update.assignee)

        params.append(task_id)
        execute_query(f"""
            UPDATE roadmap_tasks SET {", ".join(set_clauses)} WHERE id = ?
        """, tuple(params), fetch="none")

        result = execute_query("""
            SELECT id, requirement_id, title, description, status, priority, assignee,
                   created_at, updated_at
            FROM roadmap_tasks WHERE id = ?
        """, (task_id,), fetch="one")
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating roadmap task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/roadmap/tasks/{task_id}", status_code=204)
async def delete_roadmap_task(task_id: str):
    """Delete a roadmap task."""
    try:
        execute_query("DELETE FROM roadmap_tasks WHERE id = ?", (task_id,), fetch="none")
    except Exception as e:
        logger.error(f"Error deleting roadmap task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# TEST PLAN / TEST CASE ENDPOINTS (MP-013)
# ============================================

@router.get("/roadmap/test-plans")
async def list_test_plans(requirement_id: Optional[str] = Query(None)):
    """List test plans, optionally filtered by requirement."""
    try:
        if requirement_id:
            plans = execute_query("""
                SELECT id, requirement_id, name, created_at
                FROM test_plans WHERE requirement_id = ?
                ORDER BY created_at DESC
            """, (requirement_id,), fetch="all") or []
        else:
            plans = execute_query("""
                SELECT id, requirement_id, name, created_at
                FROM test_plans ORDER BY created_at DESC
            """, fetch="all") or []

        for plan in plans:
            cases = execute_query("""
                SELECT id, test_plan_id, title, expected_result, status, executed_at
                FROM test_cases WHERE test_plan_id = ?
                ORDER BY title
            """, (plan['id'],), fetch="all") or []
            plan['test_cases'] = cases

        return {"test_plans": plans, "total": len(plans)}
    except Exception as e:
        logger.error(f"Error listing test plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roadmap/test-plans", status_code=201)
async def create_test_plan(plan: TestPlanCreate):
    """Create a test plan with optional test cases."""
    try:
        import uuid
        plan_id = str(uuid.uuid4())
        execute_query("""
            INSERT INTO test_plans (id, requirement_id, name)
            VALUES (?, ?, ?)
        """, (plan_id, plan.requirement_id, plan.name), fetch="none")

        for tc in plan.test_cases:
            tc_id = str(uuid.uuid4())
            execute_query("""
                INSERT INTO test_cases (id, test_plan_id, title, expected_result)
                VALUES (?, ?, ?, ?)
            """, (tc_id, plan_id, tc.title, tc.expected_result), fetch="none")

        result = execute_query(
            "SELECT id, requirement_id, name, created_at FROM test_plans WHERE id = ?",
            (plan_id,), fetch="one"
        )
        cases = execute_query(
            "SELECT id, test_plan_id, title, expected_result, status, executed_at FROM test_cases WHERE test_plan_id = ?",
            (plan_id,), fetch="all"
        ) or []
        result['test_cases'] = cases
        return result
    except Exception as e:
        logger.error(f"Error creating test plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/roadmap/test-cases/{case_id}")
async def update_test_case(case_id: str, update: TestCaseUpdate):
    """Update a test case status."""
    try:
        set_clauses = []
        params = []
        if update.status is not None:
            set_clauses.append("status = ?")
            params.append(update.status.value)
        if update.executed_at is not None:
            set_clauses.append("executed_at = ?")
            params.append(update.executed_at)
        elif update.status is not None and update.status.value != 'pending':
            set_clauses.append("executed_at = GETDATE()")

        if not set_clauses:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.append(case_id)
        execute_query(f"""
            UPDATE test_cases SET {", ".join(set_clauses)} WHERE id = ?
        """, tuple(params), fetch="none")

        result = execute_query(
            "SELECT id, test_plan_id, title, expected_result, status, executed_at FROM test_cases WHERE id = ?",
            (case_id,), fetch="one"
        )
        if not result:
            raise HTTPException(status_code=404, detail="Test case not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating test case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roadmap/test-plans/{plan_id}/cases", status_code=201)
async def add_test_case(plan_id: str, case: TestCaseCreate):
    """Add a test case to an existing test plan."""
    try:
        import uuid
        tc_id = str(uuid.uuid4())
        execute_query("""
            INSERT INTO test_cases (id, test_plan_id, title, expected_result)
            VALUES (?, ?, ?, ?)
        """, (tc_id, plan_id, case.title, case.expected_result), fetch="none")

        result = execute_query(
            "SELECT id, test_plan_id, title, expected_result, status, executed_at FROM test_cases WHERE id = ?",
            (tc_id,), fetch="one"
        )
        return result
    except Exception as e:
        logger.error(f"Error adding test case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/roadmap/test-plans/{plan_id}", status_code=204)
async def delete_test_plan(plan_id: str):
    """Delete a test plan and its test cases."""
    try:
        execute_query("DELETE FROM test_cases WHERE test_plan_id = ?", (plan_id,), fetch="none")
        execute_query("DELETE FROM test_plans WHERE id = ?", (plan_id,), fetch="none")
    except Exception as e:
        logger.error(f"Error deleting test plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# DEPENDENCY ENDPOINTS (MP-014)
# ============================================

@router.get("/roadmap/dependencies")
async def list_dependencies(requirement_id: Optional[str] = Query(None)):
    """List requirement dependencies."""
    try:
        if requirement_id:
            results = execute_query("""
                SELECT d.id, d.requirement_id, d.depends_on_id, d.created_at,
                       r.code as depends_on_code, r.title as depends_on_title,
                       p.code as depends_on_project_code
                FROM requirement_dependencies d
                JOIN roadmap_requirements r ON d.depends_on_id = r.id
                JOIN roadmap_projects p ON r.project_id = p.id
                WHERE d.requirement_id = ?
                ORDER BY p.code, r.code
            """, (requirement_id,), fetch="all") or []
        else:
            results = execute_query("""
                SELECT d.id, d.requirement_id, d.depends_on_id, d.created_at,
                       r.code as depends_on_code, r.title as depends_on_title,
                       p.code as depends_on_project_code
                FROM requirement_dependencies d
                JOIN roadmap_requirements r ON d.depends_on_id = r.id
                JOIN roadmap_projects p ON r.project_id = p.id
                ORDER BY d.requirement_id, p.code, r.code
            """, fetch="all") or []

        return {"dependencies": results, "total": len(results)}
    except Exception as e:
        logger.error(f"Error listing dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roadmap/dependencies", status_code=201)
async def create_dependency(dep: DependencyCreate):
    """Create a requirement dependency link."""
    try:
        if dep.requirement_id == dep.depends_on_id:
            raise HTTPException(status_code=400, detail="A requirement cannot depend on itself")

        import uuid
        dep_id = str(uuid.uuid4())
        execute_query("""
            INSERT INTO requirement_dependencies (id, requirement_id, depends_on_id)
            VALUES (?, ?, ?)
        """, (dep_id, dep.requirement_id, dep.depends_on_id), fetch="none")

        result = execute_query("""
            SELECT d.id, d.requirement_id, d.depends_on_id, d.created_at,
                   r.code as depends_on_code, r.title as depends_on_title,
                   p.code as depends_on_project_code
            FROM requirement_dependencies d
            JOIN roadmap_requirements r ON d.depends_on_id = r.id
            JOIN roadmap_projects p ON r.project_id = p.id
            WHERE d.id = ?
        """, (dep_id,), fetch="one")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating dependency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/roadmap/dependencies/{dep_id}", status_code=204)
async def delete_dependency(dep_id: str):
    """Delete a requirement dependency."""
    try:
        execute_query("DELETE FROM requirement_dependencies WHERE id = ?", (dep_id,), fetch="none")
    except Exception as e:
        logger.error(f"Error deleting dependency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# AUTO-CLOSE ON UAT APPROVAL (MP-015)
# ============================================

@router.post("/roadmap/requirements/{requirement_id}/auto-close")
async def auto_close_requirement(requirement_id: str):
    """Auto-close a requirement when its UAT is approved. Sets status to done."""
    try:
        req = execute_query(
            "SELECT id, status FROM roadmap_requirements WHERE id = ?",
            (requirement_id,), fetch="one"
        )
        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")

        execute_query("""
            UPDATE roadmap_requirements SET status = 'closed', updated_at = GETDATE()
            WHERE id = ?
        """, (requirement_id,), fetch="none")

        return {"message": f"Requirement {requirement_id} auto-closed to closed", "previous_status": req['status']}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-closing requirement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STATUS TRANSITION + HISTORY (MP-MS3 Phase 2)
# ============================================

# Valid status transitions (pipeline order)
VALID_TRANSITIONS = {
    'backlog': ['draft', 'deferred'],
    'draft': ['prompt_ready', 'backlog', 'deferred'],
    'prompt_ready': ['approved', 'draft', 'deferred'],
    'approved': ['executing', 'prompt_ready', 'deferred'],
    'executing': ['handoff', 'needs_fixes', 'deferred'],
    'handoff': ['uat', 'executing', 'deferred'],
    'uat': ['closed', 'needs_fixes', 'deferred'],
    'closed': ['backlog'],  # reopen
    'needs_fixes': ['draft', 'prompt_ready', 'executing', 'deferred'],
    'deferred': ['backlog', 'draft', 'prompt_ready', 'approved', 'executing'],
}


@router.patch("/roadmap/requirements/{requirement_id}/status", response_model=StatusTransitionResponse)
async def transition_requirement_status(requirement_id: str, body: StatusTransitionRequest):
    """Transition a requirement to a new pipeline status with validation and history tracking."""
    try:
        req = execute_query(
            "SELECT id, code, status FROM roadmap_requirements WHERE id = ?",
            (requirement_id,), fetch="one"
        )
        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")

        current_status = req['status']
        new_status = body.status.value

        if current_status == new_status:
            return StatusTransitionResponse(
                id=req['id'], code=req['code'], status=new_status,
                previous_status=current_status, transition_recorded=False
            )

        # Validate transition
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: {current_status} → {new_status}. Allowed: {', '.join(allowed)}"
            )

        # Update status
        execute_query("""
            UPDATE roadmap_requirements SET status = ?, updated_at = GETDATE()
            WHERE id = ?
        """, (new_status, requirement_id), fetch="none")

        # Record history (overrides trigger's 'system' with actual changed_by)
        history_result = execute_query("""
            UPDATE requirement_history
            SET changed_by = ?, sprint_id = ?, notes = ?
            WHERE requirement_id = ? AND field_name = 'status'
              AND old_value = ? AND new_value = ?
              AND changed_at >= DATEADD(SECOND, -5, GETDATE())
        """, (body.changed_by, body.sprint_id, body.notes,
              requirement_id, current_status, new_status), fetch="none")

        # Get the history entry ID
        history_row = execute_query("""
            SELECT TOP 1 id FROM requirement_history
            WHERE requirement_id = ? AND field_name = 'status' AND new_value = ?
            ORDER BY changed_at DESC
        """, (requirement_id, new_status), fetch="one")

        return StatusTransitionResponse(
            id=req['id'], code=req['code'], status=new_status,
            previous_status=current_status, transition_recorded=True,
            history_id=history_row['id'] if history_row else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transitioning status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/roadmap/requirements/status/batch")
async def batch_transition_status(body: BatchStatusRequest):
    """Batch update status for multiple requirements."""
    try:
        results = []
        for req_id in body.ids:
            req = execute_query(
                "SELECT id, code, status FROM roadmap_requirements WHERE id = ?",
                (req_id,), fetch="one"
            )
            if not req:
                results.append({"id": req_id, "error": "not found"})
                continue

            current_status = req['status']
            new_status = body.status.value

            allowed = VALID_TRANSITIONS.get(current_status, [])
            if new_status not in allowed:
                results.append({"id": req_id, "code": req['code'], "error": f"Invalid: {current_status} → {new_status}"})
                continue

            execute_query("""
                UPDATE roadmap_requirements SET status = ?, updated_at = GETDATE()
                WHERE id = ?
            """, (new_status, req_id), fetch="none")

            # Update trigger history with changed_by
            execute_query("""
                UPDATE requirement_history
                SET changed_by = ?, sprint_id = ?
                WHERE requirement_id = ? AND field_name = 'status'
                  AND old_value = ? AND new_value = ?
                  AND changed_at >= DATEADD(SECOND, -5, GETDATE())
            """, (body.changed_by, body.sprint_id, req_id, current_status, new_status), fetch="none")

            results.append({"id": req_id, "code": req['code'], "status": new_status, "previous": current_status})

        return {"updated": len([r for r in results if 'status' in r]), "results": results}
    except Exception as e:
        logger.error(f"Error batch updating status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/requirements/{requirement_id}/history", response_model=RequirementHistoryResponse)
async def get_requirement_history(requirement_id: str):
    """Get the full change history for a requirement."""
    try:
        req = execute_query(
            "SELECT id, code, title, status FROM roadmap_requirements WHERE id = ?",
            (requirement_id,), fetch="one"
        )
        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")

        rows = execute_query("""
            SELECT id, changed_at, changed_by, field_name, old_value, new_value, sprint_id, notes
            FROM requirement_history
            WHERE requirement_id = ?
            ORDER BY changed_at ASC
        """, (requirement_id,), fetch="all") or []

        history = [HistoryEntry(
            id=r['id'], changed_at=r['changed_at'], changed_by=r['changed_by'],
            field_name=r['field_name'], old_value=r.get('old_value'),
            new_value=r.get('new_value'), sprint_id=r.get('sprint_id'),
            notes=r.get('notes')
        ) for r in rows]

        return RequirementHistoryResponse(
            requirement_id=req['id'], code=req['code'], title=req['title'],
            current_status=req['status'], history=history
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/wip")
async def get_wip_summary():
    """Get WIP pipeline summary — counts by status and active sprints."""
    try:
        # Pipeline counts
        status_rows = execute_query("""
            SELECT status, COUNT(*) as cnt
            FROM roadmap_requirements
            GROUP BY status
        """, fetch="all") or []
        pipeline = {s: 0 for s in ['backlog','draft','prompt_ready','approved','executing','handoff','uat','closed','needs_fixes','deferred']}
        for r in status_rows:
            pipeline[r['status']] = int(r['cnt'])

        # Active sprints (items with sprint_id in active states)
        sprint_rows = execute_query("""
            SELECT r.sprint_id, p.name as project_name, r.status, r.code
            FROM roadmap_requirements r
            JOIN roadmap_projects p ON r.project_id = p.id
            WHERE r.sprint_id IS NOT NULL
              AND r.status IN ('approved','executing','handoff','uat','needs_fixes')
            ORDER BY r.sprint_id, r.code
        """, fetch="all") or []

        sprints_map = {}
        for r in sprint_rows:
            sid = r['sprint_id']
            if sid not in sprints_map:
                sprints_map[sid] = {"sprint_id": sid, "project": r['project_name'], "items": [], "status": r['status']}
            sprints_map[sid]["items"].append(r['code'])

        active_sprints = list(sprints_map.values())
        for s in active_sprints:
            s["item_count"] = len(s["items"])

        return {"pipeline": pipeline, "active_sprints": active_sprints}
    except Exception as e:
        logger.error(f"Error getting WIP summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ATTACHMENTS (MP-MS3 Phase 3)
# ============================================

@router.post("/roadmap/requirements/{requirement_id}/attachments")
async def upload_attachment(
    requirement_id: str,
    file: UploadFile = File(...),
    description: str = Form(""),
    uploaded_by: str = Form("PL"),
):
    """Upload a file attachment to a requirement. Stores in GCS."""
    try:
        req = execute_query(
            "SELECT id FROM roadmap_requirements WHERE id = ?",
            (requirement_id,), fetch="one"
        )
        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")

        # Upload to GCS
        from google.cloud import storage as gcs
        client = gcs.Client()
        bucket = client.bucket("corey-handoff-bridge")
        storage_key = f"attachments/{requirement_id}/{file.filename}"
        blob = bucket.blob(storage_key)
        content = await file.read()
        blob.upload_from_string(content, content_type=file.content_type)

        # Record in DB
        execute_query("""
            INSERT INTO requirement_attachments
                (requirement_id, filename, content_type, file_size, storage_key, uploaded_by, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (requirement_id, file.filename, file.content_type or "application/octet-stream",
              len(content), storage_key, uploaded_by, description), fetch="none")

        # Get the new attachment record
        att = execute_query("""
            SELECT TOP 1 id, filename, content_type, file_size, storage_key, created_at
            FROM requirement_attachments
            WHERE requirement_id = ? AND filename = ?
            ORDER BY created_at DESC
        """, (requirement_id, file.filename), fetch="one")

        return {
            "attachment_id": att['id'] if att else None,
            "filename": file.filename,
            "url": f"https://storage.googleapis.com/corey-handoff-bridge/{storage_key}",
            "content_type": file.content_type,
            "file_size": len(content),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/requirements/{requirement_id}/attachments")
async def list_attachments(requirement_id: str):
    """List all attachments for a requirement."""
    try:
        rows = execute_query("""
            SELECT id, filename, content_type, file_size, storage_key, uploaded_by, description, created_at
            FROM requirement_attachments
            WHERE requirement_id = ?
            ORDER BY created_at DESC
        """, (requirement_id,), fetch="all") or []

        return {"attachments": [{
            "id": r['id'],
            "filename": r['filename'],
            "content_type": r['content_type'],
            "file_size": r['file_size'],
            "url": f"https://storage.googleapis.com/corey-handoff-bridge/{r['storage_key']}",
            "uploaded_by": r['uploaded_by'],
            "description": r.get('description'),
            "created_at": str(r['created_at']),
        } for r in rows]}
    except Exception as e:
        logger.error(f"Error listing attachments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CC PROMPTS (MP-MS3 Phase 3)
# ============================================

@router.post("/roadmap/prompts")
async def create_prompt(body: dict):
    """Create a CC prompt for a sprint."""
    try:
        required = ['content', 'sprint_id', 'project_id']
        for field in required:
            if field not in body:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        execute_query("""
            INSERT INTO cc_prompts (sprint_id, project_id, content, status, version_before, version_after, estimated_hours)
            VALUES (?, ?, ?, 'draft', ?, ?, ?)
        """, (body['sprint_id'], body['project_id'], body['content'],
              body.get('version_before'), body.get('version_after'),
              body.get('estimated_hours')), fetch="none")

        prompt = execute_query("""
            SELECT TOP 1 id, sprint_id, status, created_at
            FROM cc_prompts
            WHERE sprint_id = ? AND project_id = ?
            ORDER BY created_at DESC
        """, (body['sprint_id'], body['project_id']), fetch="one")

        prompt_id = prompt['id'] if prompt else None
        return {
            "prompt_id": prompt_id,
            "sprint_id": body['sprint_id'],
            "status": "draft",
            "review_url": f"/api/roadmap/prompts/{prompt_id}/content" if prompt_id else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/prompts")
async def list_prompts(status: Optional[str] = None):
    """List all CC prompts with optional status filter."""
    try:
        if status:
            rows = execute_query("""
                SELECT p.id, p.sprint_id, p.project_id, p.status, p.version_before, p.version_after,
                       p.estimated_hours, p.approved_at, p.approved_by, p.created_at, p.updated_at,
                       proj.name as project_name, proj.code as project_code
                FROM cc_prompts p
                JOIN roadmap_projects proj ON p.project_id = proj.id
                WHERE p.status = ?
                ORDER BY p.created_at DESC
            """, (status,), fetch="all") or []
        else:
            rows = execute_query("""
                SELECT p.id, p.sprint_id, p.project_id, p.status, p.version_before, p.version_after,
                       p.estimated_hours, p.approved_at, p.approved_by, p.created_at, p.updated_at,
                       proj.name as project_name, proj.code as project_code
                FROM cc_prompts p
                JOIN roadmap_projects proj ON p.project_id = proj.id
                ORDER BY p.created_at DESC
            """, fetch="all") or []

        return {"prompts": [{
            "id": r['id'], "sprint_id": r['sprint_id'], "project_id": r['project_id'],
            "project_name": r.get('project_name'), "project_code": r.get('project_code'),
            "status": r['status'], "version_before": r.get('version_before'),
            "version_after": r.get('version_after'), "estimated_hours": r.get('estimated_hours'),
            "approved_at": str(r['approved_at']) if r.get('approved_at') else None,
            "approved_by": r.get('approved_by'),
            "created_at": str(r['created_at']), "updated_at": str(r['updated_at']),
        } for r in rows]}
    except Exception as e:
        logger.error(f"Error listing prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/prompts/active")
async def list_active_prompts():
    """List non-completed prompts."""
    try:
        rows = execute_query("""
            SELECT p.id, p.sprint_id, p.project_id, p.status, p.version_before, p.version_after,
                   p.estimated_hours, p.created_at, proj.name as project_name, proj.code as project_code
            FROM cc_prompts p
            JOIN roadmap_projects proj ON p.project_id = proj.id
            WHERE p.status IN ('draft', 'prompt_ready', 'approved', 'sent')
            ORDER BY p.created_at DESC
        """, fetch="all") or []

        return {"prompts": [{
            "id": r['id'], "sprint_id": r['sprint_id'], "project_name": r.get('project_name'),
            "project_code": r.get('project_code'), "status": r['status'],
            "version_before": r.get('version_before'), "version_after": r.get('version_after'),
            "estimated_hours": r.get('estimated_hours'), "created_at": str(r['created_at']),
        } for r in rows]}
    except Exception as e:
        logger.error(f"Error listing active prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/prompts/{prompt_id}/content")
async def get_prompt_content(prompt_id: int):
    """Get the full content of a CC prompt for review."""
    try:
        prompt = execute_query(
            "SELECT id, sprint_id, content, status FROM cc_prompts WHERE id = ?",
            (prompt_id,), fetch="one"
        )
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        return {"id": prompt['id'], "sprint_id": prompt['sprint_id'],
                "content": prompt['content'], "status": prompt['status']}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roadmap/prompts/{prompt_id}/approve")
async def approve_prompt(prompt_id: int, body: dict = None):
    """Approve a CC prompt. Returns a handoff URL for CC."""
    try:
        prompt = execute_query(
            "SELECT id, sprint_id, status FROM cc_prompts WHERE id = ?",
            (prompt_id,), fetch="one"
        )
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        approved_by = (body or {}).get('approved_by', 'PL')
        execute_query("""
            UPDATE cc_prompts SET status = 'approved', approved_at = GETDATE(),
                   approved_by = ?, updated_at = GETDATE()
            WHERE id = ?
        """, (approved_by, prompt_id), fetch="none")

        handoff_url = f"https://metapm.rentyourcio.com/api/roadmap/prompts/{prompt_id}/handoff"
        return {
            "approved": True,
            "prompt_id": prompt_id,
            "sprint_id": prompt['sprint_id'],
            "handoff_url": handoff_url,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/prompts/{prompt_id}/handoff", response_class=PlainTextResponse)
async def get_prompt_handoff(prompt_id: int):
    """Get raw markdown of an approved prompt. CC reads this URL directly."""
    try:
        prompt = execute_query(
            "SELECT id, content, status FROM cc_prompts WHERE id = ?",
            (prompt_id,), fetch="one"
        )
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")
        if prompt['status'] not in ('approved', 'sent', 'completed'):
            raise HTTPException(status_code=403, detail=f"Prompt not yet approved (status: {prompt['status']})")

        # Mark as sent
        execute_query(
            "UPDATE cc_prompts SET status = 'sent', updated_at = GETDATE() WHERE id = ? AND status = 'approved'",
            (prompt_id,), fetch="none"
        )

        return prompt['content']
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt handoff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# REQUIREMENT LINKS (MP-MS3 Phase 4)
# ============================================

@router.post("/roadmap/requirements/{requirement_id}/links")
async def add_requirement_link(requirement_id: str, body: dict):
    """Add a link to a requirement (handoff, RAG doc, external URL, etc.)."""
    try:
        req = execute_query(
            "SELECT id FROM roadmap_requirements WHERE id = ?",
            (requirement_id,), fetch="one"
        )
        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")

        url = body.get('url')
        link_type = body.get('link_type', 'external')
        description = body.get('description')

        if not url:
            raise HTTPException(status_code=400, detail="url is required")

        execute_query("""
            INSERT INTO requirement_links (requirement_id, url, link_type, description)
            VALUES (?, ?, ?, ?)
        """, (requirement_id, url, link_type, description), fetch="none")

        link = execute_query("""
            SELECT TOP 1 id, requirement_id, url, link_type, description, created_at
            FROM requirement_links
            WHERE requirement_id = ? AND url = ?
            ORDER BY created_at DESC
        """, (requirement_id, url), fetch="one")

        return {
            "id": link['id'],
            "requirement_id": link['requirement_id'],
            "url": link['url'],
            "link_type": link['link_type'],
            "description": link.get('description'),
            "created_at": str(link['created_at']),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/requirements/{requirement_id}/links")
async def list_requirement_links(requirement_id: str):
    """List all links for a requirement."""
    try:
        rows = execute_query("""
            SELECT id, requirement_id, url, link_type, description, created_at
            FROM requirement_links
            WHERE requirement_id = ?
            ORDER BY created_at DESC
        """, (requirement_id,), fetch="all") or []

        return {"links": [{
            "id": r['id'],
            "requirement_id": r['requirement_id'],
            "url": r['url'],
            "link_type": r['link_type'],
            "description": r.get('description'),
            "created_at": str(r['created_at']),
        } for r in rows]}
    except Exception as e:
        logger.error(f"Error listing links: {e}")
        raise HTTPException(status_code=500, detail=str(e))

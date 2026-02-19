"""
MetaPM Roadmap API Router
Project, Requirement, and Sprint management endpoints.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

from app.core.database import execute_query
from app.schemas.roadmap import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    SprintCreate, SprintUpdate, SprintResponse, SprintListResponse,
    RequirementCreate, RequirementUpdate, RequirementResponse, RequirementListResponse,
    ProjectRoadmapItem, RoadmapResponse,
    ProjectStatus, RequirementStatus, RequirementType, RequirementPriority, SprintStatus
)

logger = logging.getLogger(__name__)

router = APIRouter()


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
            SELECT id, code, name, emoji, color, current_version, status,
                   repo_url, deploy_url, created_at, updated_at
            FROM roadmap_projects
            {where_clause}
            ORDER BY name
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
            SELECT id, code, name, emoji, color, current_version, status,
                   repo_url, deploy_url, created_at, updated_at
            FROM roadmap_projects WHERE id = ?
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
            INSERT INTO roadmap_projects (id, code, name, emoji, color, current_version, status, repo_url, deploy_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project.id, project.code, project.name, project.emoji, project.color,
            project.current_version, project.status.value, project.repo_url, project.deploy_url
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
    """Delete a project. Fails if project has requirements (FK constraint)."""
    try:
        reqs = execute_query(
            "SELECT COUNT(*) as cnt FROM roadmap_requirements WHERE project_id = ?",
            (project_id,), fetch="one"
        )
        if reqs and reqs['cnt'] > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete project with {reqs['cnt']} requirements. Delete requirements first."
            )
        execute_query(
            "DELETE FROM roadmap_projects WHERE id = ?",
            (project_id,), fetch="none"
        )
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
        if update.project_id is not None:
            set_clauses.append("project_id = ?")
            params.append(update.project_id)
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
    """Delete a sprint."""
    try:
        execute_query(
            "DELETE FROM roadmap_sprints WHERE id = ?",
            (sprint_id,), fetch="none"
        )
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
                        WHEN 'in_progress' THEN 1
                        WHEN 'uat' THEN 2
                        WHEN 'needs_fixes' THEN 3
                        WHEN 'planned' THEN 4
                        WHEN 'backlog' THEN 5
                        WHEN 'done' THEN 6
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
                SUM(CASE WHEN status = 'planned' THEN 1 ELSE 0 END) as planned,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'uat' THEN 1 ELSE 0 END) as uat,
                SUM(CASE WHEN status = 'needs_fixes' THEN 1 ELSE 0 END) as needs_fixes,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done
            FROM roadmap_requirements
        """, fetch="one")

        stats = {
            "total": stats_result['total'] or 0,
            "backlog": stats_result['backlog'] or 0,
            "planned": stats_result['planned'] or 0,
            "in_progress": stats_result['in_progress'] or 0,
            "uat": stats_result['uat'] or 0,
            "needs_fixes": stats_result['needs_fixes'] or 0,
            "done": stats_result['done'] or 0
        } if stats_result else {}

        return RoadmapResponse(projects=roadmap_items, stats=stats)
    except Exception as e:
        logger.error(f"Error getting roadmap: {e}")
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
            ('req-hl-001', 'proj-hl', 'HL-001', 'Quiz backend fix', 'bug', 'P1', 'done', '1.5.3'),
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

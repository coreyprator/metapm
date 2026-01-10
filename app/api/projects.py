"""
MetaPM Projects API
Project registry and management
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, 
    ProjectDetailResponse, ProjectListResponse, TaskSummary
)
from app.core.database import execute_query

router = APIRouter()


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[str] = Query(None, pattern="^(ACTIVE|PAUSED|COMPLETED|ARCHIVED|BLOCKED|NOT_STARTED)$"),
    theme: Optional[str] = Query(None, description="Filter by theme"),
):
    """List all projects with optional filters"""
    conditions = ["1=1"]
    params = []
    
    if status:
        conditions.append("p.Status = ?")
        params.append(status)
    
    if theme:
        conditions.append("p.Theme LIKE ?")
        params.append(f"%{theme}%")
    
    where_clause = " AND ".join(conditions)
    
    query = f"""
        SELECT 
            p.ProjectID as projectId,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            p.Theme as theme,
            p.Description as description,
            p.ProjectURL as projectUrl,
            p.GitHubRepo as githubRepo,
            p.VSCodeWorkspace as vscodeWorkspace,
            p.Status as status,
            p.Priority as priority,
            p.CreatedAt as createdAt,
            p.UpdatedAt as updatedAt,
            (SELECT COUNT(*) FROM TaskProjectLinks tpl WHERE tpl.ProjectID = p.ProjectID) as taskCount,
            (SELECT COUNT(*) FROM TaskProjectLinks tpl 
             JOIN Tasks t ON tpl.TaskID = t.TaskID 
             WHERE tpl.ProjectID = p.ProjectID AND t.Status NOT IN ('COMPLETE', 'CANCELLED')) as openTaskCount,
            (SELECT COUNT(*) FROM TaskProjectLinks tpl 
             JOIN Tasks t ON tpl.TaskID = t.TaskID 
             WHERE tpl.ProjectID = p.ProjectID AND t.Status = 'BLOCKED') as blockedTaskCount
        FROM Projects p
        WHERE {where_clause}
        ORDER BY p.Priority ASC, p.ProjectName ASC
    """
    
    rows = execute_query(query, tuple(params) if params else None, fetch="all") or []
    
    projects = [ProjectResponse(**row) for row in rows]
    
    return ProjectListResponse(projects=projects, total=len(projects))


@router.get("/{project_code}", response_model=ProjectDetailResponse)
async def get_project(project_code: str):
    """Get project details with associated tasks"""
    query = """
        SELECT 
            p.ProjectID as projectId,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            p.Theme as theme,
            p.Description as description,
            p.ProjectURL as projectUrl,
            p.GitHubRepo as githubRepo,
            p.VSCodeWorkspace as vscodeWorkspace,
            p.Status as status,
            p.Priority as priority,
            p.CreatedAt as createdAt,
            p.UpdatedAt as updatedAt,
            (SELECT COUNT(*) FROM TaskProjectLinks tpl WHERE tpl.ProjectID = p.ProjectID) as taskCount,
            (SELECT COUNT(*) FROM TaskProjectLinks tpl 
             JOIN Tasks t ON tpl.TaskID = t.TaskID 
             WHERE tpl.ProjectID = p.ProjectID AND t.Status NOT IN ('COMPLETE', 'CANCELLED')) as openTaskCount,
            (SELECT COUNT(*) FROM TaskProjectLinks tpl 
             JOIN Tasks t ON tpl.TaskID = t.TaskID 
             WHERE tpl.ProjectID = p.ProjectID AND t.Status = 'BLOCKED') as blockedTaskCount
        FROM Projects p
        WHERE p.ProjectCode = ?
    """
    
    row = execute_query(query, (project_code,), fetch="one")
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Project {project_code} not found")
    
    # Get tasks for this project
    tasks_query = """
        SELECT 
            t.TaskID as taskId,
            t.Title as title,
            t.Priority as priority,
            t.Status as status,
            t.DueDate as dueDate,
            (SELECT STRING_AGG(c.CategoryCode, ',') 
             FROM TaskCategoryLinks tcl 
             JOIN Categories c ON tcl.CategoryID = c.CategoryID 
             WHERE tcl.TaskID = t.TaskID) as categories
        FROM Tasks t
        JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID
        JOIN Projects p ON tpl.ProjectID = p.ProjectID
        WHERE p.ProjectCode = ?
        ORDER BY t.Priority ASC, t.DueDate ASC
    """
    
    task_rows = execute_query(tasks_query, (project_code,), fetch="all") or []
    tasks = []
    for task_row in task_rows:
        task = dict(task_row)
        task["categories"] = task_row["categories"].split(",") if task_row.get("categories") else []
        tasks.append(TaskSummary(**task))
    
    # Get linked projects
    links_query = """
        SELECT DISTINCT p2.ProjectCode
        FROM CrossProjectLinks cpl
        JOIN Projects p1 ON cpl.SourceProjectID = p1.ProjectID
        JOIN Projects p2 ON cpl.TargetProjectID = p2.ProjectID
        WHERE p1.ProjectCode = ?
    """
    
    link_rows = execute_query(links_query, (project_code,), fetch="all") or []
    linked_projects = [r["ProjectCode"] for r in link_rows]
    
    return ProjectDetailResponse(
        **row,
        tasks=tasks,
        linkedProjects=linked_projects
    )


@router.get("/{project_code}/next")
async def get_next_sprint_task(project_code: str):
    """Get the next incomplete sprint task for a project"""
    result = execute_query("""
        SELECT TOP 1 
            t.TaskID as taskId,
            t.Title as title,
            t.Description as description,
            t.Priority as priority,
            t.SprintNumber as sprintNumber,
            t.Status as status
        FROM Tasks t
        JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID
        JOIN Projects p ON tpl.ProjectID = p.ProjectID
        WHERE p.ProjectCode = ?
          AND t.Status = 'NEW'
          AND t.SprintNumber IS NOT NULL
        ORDER BY t.SprintNumber, t.Priority
    """, (project_code,), fetch="one")
    
    if not result:
        return {"message": f"No pending sprint tasks for project {project_code}", "task": None}
    
    return {"message": "Next sprint task", "task": result}


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate):
    """Create a new project"""
    # Check for duplicate code
    existing = execute_query(
        "SELECT ProjectID FROM Projects WHERE ProjectCode = ?", 
        (project.project_code,), 
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Project code {project.project_code} already exists")
    
    query = """
        INSERT INTO Projects (ProjectCode, ProjectName, Theme, Description, ProjectURL, GitHubRepo, VSCodeWorkspace, Status, Priority)
        OUTPUT INSERTED.ProjectID
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    result = execute_query(query, (
        project.project_code,
        project.project_name,
        project.theme,
        project.description,
        project.project_url,
        project.github_repo,
        project.vscode_workspace,
        project.status,
        project.priority
    ), fetch="one")
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create project")
    
    # Fetch and return the created project
    return await get_project(project.project_code)


@router.put("/{project_code}", response_model=ProjectResponse)
async def update_project(project_code: str, project: ProjectUpdate):
    """Update an existing project"""
    # Check exists
    existing = execute_query(
        "SELECT ProjectID FROM Projects WHERE ProjectCode = ?", 
        (project_code,), 
        fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"Project {project_code} not found")
    
    # Build dynamic UPDATE
    updates = []
    params = []
    
    if project.project_name is not None:
        updates.append("ProjectName = ?")
        params.append(project.project_name)
    if project.theme is not None:
        updates.append("Theme = ?")
        params.append(project.theme)
    if project.description is not None:
        updates.append("Description = ?")
        params.append(project.description)
    if project.project_url is not None:
        updates.append("ProjectURL = ?")
        params.append(project.project_url)
    if project.github_repo is not None:
        updates.append("GitHubRepo = ?")
        params.append(project.github_repo)
    if project.vscode_workspace is not None:
        updates.append("VSCodeWorkspace = ?")
        params.append(project.vscode_workspace)
    if project.status is not None:
        updates.append("Status = ?")
        params.append(project.status)
    if project.priority is not None:
        updates.append("Priority = ?")
        params.append(project.priority)
    
    if updates:
        updates.append("UpdatedAt = GETUTCDATE()")
        params.append(project_code)
        
        query = f"UPDATE Projects SET {', '.join(updates)} WHERE ProjectCode = ?"
        execute_query(query, tuple(params), fetch="none")
    
    return await get_project(project_code)

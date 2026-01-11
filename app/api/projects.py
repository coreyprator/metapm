"""
MetaPM Projects API
===================

CRUD operations for projects with AI thread URL support.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import execute_query

router = APIRouter()


# ============================================
# MODELS
# ============================================

class ProjectCreate(BaseModel):
    projectCode: str
    projectName: str
    description: Optional[str] = None
    theme: Optional[str] = None
    status: str = "ACTIVE"
    currentAIThreadURL: Optional[str] = None


class ProjectUpdate(BaseModel):
    projectName: Optional[str] = None
    description: Optional[str] = None
    theme: Optional[str] = None
    status: Optional[str] = None
    currentAIThreadURL: Optional[str] = None


# ============================================
# ENDPOINTS
# ============================================

@router.get("")
async def list_projects(
    theme: Optional[str] = None,
    status: Optional[str] = None
):
    """List all projects."""
    query = """
        SELECT 
            ProjectID as projectId,
            ProjectCode as projectCode,
            ProjectName as projectName,
            Description as description,
            Theme as theme,
            Status as status,
            CurrentAIThreadURL as currentAIThreadURL,
            CreatedAt as createdAt,
            UpdatedAt as updatedAt
        FROM Projects
        WHERE 1=1
    """
    
    if theme:
        query += f" AND Theme = '{theme}'"
    if status:
        query += f" AND Status = '{status}'"
    
    query += " ORDER BY Theme, ProjectCode"
    
    projects = execute_query(query)
    return {"projects": projects, "count": len(projects)}


@router.get("/{project_code}")
async def get_project(project_code: str):
    """Get a specific project by code."""
    query = """
        SELECT 
            ProjectID as projectId,
            ProjectCode as projectCode,
            ProjectName as projectName,
            Description as description,
            Theme as theme,
            Status as status,
            CurrentAIThreadURL as currentAIThreadURL,
            CreatedAt as createdAt,
            UpdatedAt as updatedAt
        FROM Projects
        WHERE ProjectCode = ?
    """
    
    project = execute_query(query, (project_code,), fetch="one")
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get task count
    task_count = execute_query("""
        SELECT COUNT(*) as count FROM TaskProjectLinks tpl
        JOIN Tasks t ON tpl.TaskID = t.TaskID
        WHERE tpl.ProjectID = ? AND t.Status != 'DELETED'
    """, (project['projectId'],), fetch="one")
    project['taskCount'] = task_count['count'] if task_count else 0
    
    # Get recent violations
    violations = execute_query("""
        SELECT TOP 5
            v.ViolationID as violationId,
            r.RuleCode as ruleCode,
            v.Context as context,
            v.CreatedAt as createdAt
        FROM MethodologyViolations v
        JOIN MethodologyRules r ON v.RuleID = r.RuleID
        WHERE v.ProjectID = ?
        ORDER BY v.CreatedAt DESC
    """, (project['projectId'],))
    project['recentViolations'] = violations
    
    return project


@router.get("/{project_code}/tasks")
async def get_project_tasks(
    project_code: str,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get all tasks for a project."""
    project = execute_query(
        "SELECT ProjectID FROM Projects WHERE ProjectCode = ?",
        (project_code,),
        fetch="one"
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = """
        SELECT 
            t.TaskID as taskId,
            t.Title as title,
            t.Description as description,
            t.Priority as priority,
            t.Status as status,
            t.DueDate as dueDate,
            t.CreatedAt as createdAt
        FROM Tasks t
        JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID
        WHERE tpl.ProjectID = ?
    """
    
    if status:
        query += f" AND t.Status = '{status}'"
    else:
        query += " AND t.Status != 'DELETED'"
    
    query += f" ORDER BY t.Priority, t.CreatedAt DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
    
    tasks = execute_query(query, (project['ProjectID'],))
    return {"projectCode": project_code, "tasks": tasks, "count": len(tasks)}


@router.post("")
async def create_project(project: ProjectCreate):
    """Create a new project."""
    # Check for duplicate
    existing = execute_query(
        "SELECT ProjectID FROM Projects WHERE ProjectCode = ?",
        (project.projectCode,),
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail="Project code already exists")
    
    query = """
        INSERT INTO Projects (ProjectCode, ProjectName, Description, Theme, Status, CurrentAIThreadURL)
        OUTPUT INSERTED.ProjectID, INSERTED.ProjectCode
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    result = execute_query(
        query,
        (project.projectCode, project.projectName, project.description, 
         project.theme, project.status, project.currentAIThreadURL),
        fetch="one"
    )
    
    return {"message": "Project created", "project": result}


@router.put("/{project_code}")
async def update_project(project_code: str, project: ProjectUpdate):
    """Update a project."""
    existing = execute_query(
        "SELECT ProjectID FROM Projects WHERE ProjectCode = ?",
        (project_code,),
        fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Build dynamic update
    updates = []
    params = []
    
    if project.projectName is not None:
        updates.append("ProjectName = ?")
        params.append(project.projectName)
    if project.description is not None:
        updates.append("Description = ?")
        params.append(project.description)
    if project.theme is not None:
        updates.append("Theme = ?")
        params.append(project.theme)
    if project.status is not None:
        updates.append("Status = ?")
        params.append(project.status)
    if project.currentAIThreadURL is not None:
        updates.append("CurrentAIThreadURL = ?")
        params.append(project.currentAIThreadURL)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("UpdatedAt = GETUTCDATE()")
    params.append(project_code)
    
    query = f"UPDATE Projects SET {', '.join(updates)} WHERE ProjectCode = ?"
    execute_query(query, tuple(params), fetch="none")
    
    return {"message": "Project updated", "projectCode": project_code}


@router.put("/{project_code}/ai-thread")
async def update_ai_thread(project_code: str, url: str):
    """Quick update for AI thread URL."""
    execute_query(
        "UPDATE Projects SET CurrentAIThreadURL = ?, UpdatedAt = GETUTCDATE() WHERE ProjectCode = ?",
        (url, project_code),
        fetch="none"
    )
    return {"message": "AI thread URL updated", "projectCode": project_code, "url": url}


@router.delete("/{project_code}")
async def delete_project(project_code: str):
    """Delete a project (soft delete)."""
    execute_query(
        "UPDATE Projects SET Status = 'DELETED', UpdatedAt = GETUTCDATE() WHERE ProjectCode = ?",
        (project_code,),
        fetch="none"
    )
    return {"message": "Project deleted", "projectCode": project_code}

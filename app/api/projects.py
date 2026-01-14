"""
MetaPM Projects API - Enhanced
==============================

Full CRUD operations for projects with:
- Rich text/HTML content support
- AI thread URL tracking
- VS Code and GitHub links
- Tech stack and production URL
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
    projectURL: Optional[str] = None
    gitHubRepo: Optional[str] = None
    vscodeWorkspace: Optional[str] = None
    priority: Optional[int] = 3


class ProjectUpdate(BaseModel):
    projectName: Optional[str] = None
    description: Optional[str] = None
    theme: Optional[str] = None
    status: Optional[str] = None
    projectURL: Optional[str] = None
    gitHubRepo: Optional[str] = None
    vscodeWorkspace: Optional[str] = None
    priority: Optional[int] = None

# ============================================
# ENDPOINTS
# ============================================

@router.get("")
async def list_projects(
    theme: Optional[str] = None,
    status: Optional[str] = None,
    include_content: bool = Query(default=False, description="Include full HTML content")
):
    """List all projects."""
    # Build column list based on include_content
    columns = """
        ProjectID as projectId,
        ProjectCode as projectCode,
        ProjectName as projectName,
        Description as description,
        Theme as theme,
        Status as status,
        ProjectURL as productionURL,
        GitHubRepo as gitHubURL,
        VSCodeWorkspace as vsCodePath,
        Priority as priority,
        CreatedAt as createdAt,
        UpdatedAt as updatedAt
    """
    
    query = f"SELECT {columns} FROM Projects WHERE 1=1"
    
    if theme:
        query += f" AND Theme = '{theme}'"
    if status:
        query += f" AND Status = '{status}'"
    else:
        query += " AND Status != 'DELETED'"
    
    query += " ORDER BY Theme, ProjectCode"
    
    projects = execute_query(query)
    
    # Get task counts for each project
    for project in projects:
        task_count = execute_query("""
            SELECT COUNT(*) as count FROM TaskProjectLinks tpl
            JOIN Tasks t ON tpl.TaskID = t.TaskID
            WHERE tpl.ProjectID = ? AND t.Status != 'DELETED'
        """, (project['projectId'],), fetch="one")
        project['taskCount'] = task_count['count'] if task_count else 0
        
        # Get violation count
        violation_count = execute_query("""
            SELECT COUNT(*) as count FROM MethodologyViolations
            WHERE ProjectID = ?
        """, (project['projectId'],), fetch="one")
        project['violationCount'] = violation_count['count'] if violation_count else 0
    
    # Get unique themes for filter
    themes = execute_query("SELECT DISTINCT Theme FROM Projects WHERE Theme IS NOT NULL ORDER BY Theme")
    
    return {
        "projects": projects,
        "count": len(projects),
        "themes": [t['Theme'] for t in themes]
    }


@router.get("/{project_code}")
async def get_project(project_code: str):
    """Get a specific project by code with full details."""
    query = """
        SELECT 
            ProjectID as projectId,
            ProjectCode as projectCode,
            ProjectName as projectName,
            Description as description,
            Theme as theme,
            Status as status,
            ProjectURL as productionURL,
            GitHubRepo as gitHubURL,
            VSCodeWorkspace as vsCodePath,
            Priority as priority,
            CreatedAt as createdAt,
            UpdatedAt as updatedAt
        FROM Projects
        WHERE ProjectCode = ?
    """
    
    project = execute_query(query, (project_code,), fetch="one")
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get task count and recent tasks
    tasks = execute_query("""
        SELECT TOP 10
            t.TaskID as taskId,
            t.Title as title,
            t.Status as status,
            t.Priority as priority,
            t.DueDate as dueDate
        FROM Tasks t
        JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID
        WHERE tpl.ProjectID = ? AND t.Status != 'DELETED'
        ORDER BY t.Priority, t.CreatedAt DESC
    """, (project['projectId'],))
    project['recentTasks'] = tasks
    project['taskCount'] = len(tasks)
    
    # Get recent violations
    violations = execute_query("""
        SELECT TOP 5
            v.ViolationID as violationId,
            r.RuleCode as ruleCode,
            r.RuleName as ruleName,
            v.Description as description,
            v.CreatedAt as createdAt
        FROM MethodologyViolations v
        JOIN MethodologyRules r ON v.RuleID = r.RuleID
        WHERE v.ProjectID = ?
        ORDER BY v.CreatedAt DESC
    """, (project['projectId'],))
    project['recentViolations'] = violations
    project['violationCount'] = len(violations)
    
    # Get recent conversations
    conversations = execute_query("""
        SELECT TOP 5
            ConversationID as conversationId,
            Title as title,
            Source as source,
            CreatedAt as createdAt
        FROM Conversations
        WHERE ProjectCode = ?
        ORDER BY CreatedAt DESC
    """, (project_code,))
    project['recentConversations'] = conversations
    
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
        INSERT INTO Projects (
            ProjectCode, ProjectName, Description, Theme, Status,
            ProjectURL, GitHubRepo, VSCodeWorkspace, Priority
        )
        OUTPUT INSERTED.ProjectID, INSERTED.ProjectCode
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    result = execute_query(
        query,
        (project.projectCode, project.projectName, project.description,
         project.theme, project.status, project.projectURL, project.gitHubRepo,
         project.vscodeWorkspace, project.priority),
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
    
    field_map = {
        'projectName': 'ProjectName',
        'description': 'Description',
        'theme': 'Theme',
        'status': 'Status',
        'projectURL': 'ProjectURL',
        'gitHubRepo': 'GitHubRepo',
        'vscodeWorkspace': 'VSCodeWorkspace',
        'priority': 'Priority'
    }
    
    for py_field, sql_field in field_map.items():
        value = getattr(project, py_field, None)
        if value is not None:
            updates.append(f"{sql_field} = ?")
            params.append(value)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("UpdatedAt = GETUTCDATE()")
    params.append(project_code)
    
    query = f"UPDATE Projects SET {', '.join(updates)} WHERE ProjectCode = ?"
    execute_query(query, tuple(params), fetch="none")
    
    return {"message": "Project updated", "projectCode": project_code}




@router.delete("/{project_code}")
async def delete_project(project_code: str, hard_delete: bool = Query(default=False)):
    """Delete a project (soft delete by default)."""
    existing = execute_query(
        "SELECT ProjectID FROM Projects WHERE ProjectCode = ?",
        (project_code,),
        fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if hard_delete:
        # Remove task links first
        execute_query(
            "DELETE FROM TaskProjectLinks WHERE ProjectID = ?",
            (existing['ProjectID'],),
            fetch="none"
        )
        # Remove violations
        execute_query(
            "DELETE FROM MethodologyViolations WHERE ProjectID = ?",
            (existing['ProjectID'],),
            fetch="none"
        )
        # Delete project
        execute_query(
            "DELETE FROM Projects WHERE ProjectCode = ?",
            (project_code,),
            fetch="none"
        )
        return {"message": "Project permanently deleted", "projectCode": project_code}
    else:
        execute_query(
            "UPDATE Projects SET Status = 'DELETED', UpdatedAt = GETUTCDATE() WHERE ProjectCode = ?",
            (project_code,),
            fetch="none"
        )
        return {"message": "Project deleted", "projectCode": project_code}

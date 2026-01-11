"""
MetaPM Tasks API - Enhanced
===========================

Full CRUD operations for tasks with project/category linking.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.core.database import execute_query

router = APIRouter()


# ============================================
# MODELS
# ============================================

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 3
    status: str = "NEW"
    dueDate: Optional[str] = None
    projects: List[str] = []  # Project codes
    categories: List[str] = []  # Category codes


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    dueDate: Optional[str] = None
    projects: Optional[List[str]] = None
    categories: Optional[List[str]] = None


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_task_with_links(task_id: int):
    """Get a task with its project and category links."""
    task = execute_query("""
        SELECT 
            t.TaskID as taskId,
            t.Title as title,
            t.Description as description,
            t.Priority as priority,
            t.Status as status,
            t.DueDate as dueDate,
            t.CreatedAt as createdAt,
            t.UpdatedAt as updatedAt
        FROM Tasks t
        WHERE t.TaskID = ?
    """, (task_id,), fetch="one")
    
    if not task:
        return None
    
    # Get linked projects
    projects = execute_query("""
        SELECT p.ProjectCode
        FROM TaskProjectLinks tpl
        JOIN Projects p ON tpl.ProjectID = p.ProjectID
        WHERE tpl.TaskID = ?
    """, (task_id,))
    task['projects'] = [p['ProjectCode'] for p in projects]
    task['projectCode'] = task['projects'][0] if task['projects'] else None
    
    # Get linked categories
    categories = execute_query("""
        SELECT c.CategoryCode
        FROM TaskCategoryLinks tcl
        JOIN Categories c ON tcl.CategoryID = c.CategoryID
        WHERE tcl.TaskID = ?
    """, (task_id,))
    task['categories'] = [c['CategoryCode'] for c in categories]
    
    return task


def link_task_to_projects(task_id: int, project_codes: List[str]):
    """Link a task to projects by code."""
    # Clear existing links
    execute_query("DELETE FROM TaskProjectLinks WHERE TaskID = ?", (task_id,), fetch="none")
    
    for code in project_codes:
        project = execute_query(
            "SELECT ProjectID FROM Projects WHERE ProjectCode = ?",
            (code,),
            fetch="one"
        )
        if project:
            execute_query(
                "INSERT INTO TaskProjectLinks (TaskID, ProjectID) VALUES (?, ?)",
                (task_id, project['ProjectID']),
                fetch="none"
            )


def link_task_to_categories(task_id: int, category_codes: List[str]):
    """Link a task to categories by code."""
    # Clear existing links
    execute_query("DELETE FROM TaskCategoryLinks WHERE TaskID = ?", (task_id,), fetch="none")
    
    for code in category_codes:
        category = execute_query(
            "SELECT CategoryID FROM Categories WHERE CategoryCode = ?",
            (code,),
            fetch="one"
        )
        if category:
            execute_query(
                "INSERT INTO TaskCategoryLinks (TaskID, CategoryID) VALUES (?, ?)",
                (task_id, category['CategoryID']),
                fetch="none"
            )


# ============================================
# ENDPOINTS
# ============================================

@router.get("")
async def list_tasks(
    status: Optional[List[str]] = Query(default=None),
    project: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[int] = None,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, le=200)
):
    """List tasks with filtering and pagination."""
    offset = (page - 1) * pageSize
    
    # Build query
    query = """
        SELECT DISTINCT
            t.TaskID as taskId,
            t.Title as title,
            t.Description as description,
            t.Priority as priority,
            t.Status as status,
            t.DueDate as dueDate,
            t.CreatedAt as createdAt,
            (SELECT TOP 1 p.ProjectCode FROM TaskProjectLinks tpl 
             JOIN Projects p ON tpl.ProjectID = p.ProjectID 
             WHERE tpl.TaskID = t.TaskID) as projectCode
        FROM Tasks t
        LEFT JOIN TaskProjectLinks tpl ON t.TaskID = tpl.TaskID
        LEFT JOIN Projects p ON tpl.ProjectID = p.ProjectID
        LEFT JOIN TaskCategoryLinks tcl ON t.TaskID = tcl.TaskID
        LEFT JOIN Categories c ON tcl.CategoryID = c.CategoryID
        WHERE 1=1
    """
    
    if status:
        status_list = "', '".join(status)
        query += f" AND t.Status IN ('{status_list}')"
    if project:
        query += f" AND p.ProjectCode = '{project}'"
    if category:
        query += f" AND c.CategoryCode = '{category}'"
    if priority:
        query += f" AND t.Priority = {priority}"
    
    # Count total
    count_query = query.replace("SELECT DISTINCT", "SELECT COUNT(DISTINCT t.TaskID) as total FROM (SELECT")
    count_query = f"SELECT COUNT(*) as total FROM ({query}) as subq"
    
    query += f" ORDER BY t.Priority, t.CreatedAt DESC OFFSET {offset} ROWS FETCH NEXT {pageSize} ROWS ONLY"
    
    tasks = execute_query(query)
    
    # Get links for each task
    for task in tasks:
        # Get all projects
        projects = execute_query("""
            SELECT p.ProjectCode FROM TaskProjectLinks tpl
            JOIN Projects p ON tpl.ProjectID = p.ProjectID
            WHERE tpl.TaskID = ?
        """, (task['taskId'],))
        task['projects'] = [p['ProjectCode'] for p in projects]
        
        # Get all categories
        categories = execute_query("""
            SELECT c.CategoryCode FROM TaskCategoryLinks tcl
            JOIN Categories c ON tcl.CategoryID = c.CategoryID
            WHERE tcl.TaskID = ?
        """, (task['taskId'],))
        task['categories'] = [c['CategoryCode'] for c in categories]
    
    return {
        "tasks": tasks,
        "page": page,
        "pageSize": pageSize,
        "total": len(tasks)  # Simplified - could do proper count
    }


@router.get("/{task_id}")
async def get_task(task_id: int):
    """Get a specific task by ID."""
    task = get_task_with_links(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("")
async def create_task(task: TaskCreate):
    """Create a new task."""
    # Insert task
    query = """
        INSERT INTO Tasks (Title, Description, Priority, Status, DueDate)
        OUTPUT INSERTED.TaskID
        VALUES (?, ?, ?, ?, ?)
    """
    
    due_date = task.dueDate if task.dueDate else None
    
    result = execute_query(
        query,
        (task.title, task.description, task.priority, task.status, due_date),
        fetch="one"
    )
    
    task_id = result['TaskID']
    
    # Link to projects
    if task.projects:
        link_task_to_projects(task_id, task.projects)
    
    # Link to categories
    if task.categories:
        link_task_to_categories(task_id, task.categories)
    
    return {"message": "Task created", "taskId": task_id, "task": get_task_with_links(task_id)}


@router.put("/{task_id}")
async def update_task(task_id: int, task: TaskUpdate):
    """Update a task."""
    # Verify task exists
    existing = execute_query("SELECT TaskID FROM Tasks WHERE TaskID = ?", (task_id,), fetch="one")
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Build dynamic update
    updates = []
    params = []
    
    if task.title is not None:
        updates.append("Title = ?")
        params.append(task.title)
    if task.description is not None:
        updates.append("Description = ?")
        params.append(task.description)
    if task.priority is not None:
        updates.append("Priority = ?")
        params.append(task.priority)
    if task.status is not None:
        updates.append("Status = ?")
        params.append(task.status)
    if task.dueDate is not None:
        updates.append("DueDate = ?")
        params.append(task.dueDate if task.dueDate else None)
    
    if updates:
        updates.append("UpdatedAt = GETUTCDATE()")
        params.append(task_id)
        
        query = f"UPDATE Tasks SET {', '.join(updates)} WHERE TaskID = ?"
        execute_query(query, tuple(params), fetch="none")
    
    # Update project links
    if task.projects is not None:
        link_task_to_projects(task_id, task.projects)
    
    # Update category links
    if task.categories is not None:
        link_task_to_categories(task_id, task.categories)
    
    return {"message": "Task updated", "task": get_task_with_links(task_id)}


@router.delete("/{task_id}")
async def delete_task(task_id: int, hard_delete: bool = Query(default=False)):
    """Delete a task."""
    # Verify task exists
    existing = execute_query("SELECT TaskID FROM Tasks WHERE TaskID = ?", (task_id,), fetch="one")
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if hard_delete:
        # Delete links first (foreign key constraints)
        execute_query("DELETE FROM TaskProjectLinks WHERE TaskID = ?", (task_id,), fetch="none")
        execute_query("DELETE FROM TaskCategoryLinks WHERE TaskID = ?", (task_id,), fetch="none")
        execute_query("DELETE FROM Tasks WHERE TaskID = ?", (task_id,), fetch="none")
        return {"message": "Task permanently deleted", "taskId": task_id}
    else:
        # Soft delete - just mark as DELETED status
        execute_query(
            "UPDATE Tasks SET Status = 'DELETED', UpdatedAt = GETUTCDATE() WHERE TaskID = ?",
            (task_id,),
            fetch="none"
        )
        return {"message": "Task deleted", "taskId": task_id}


@router.post("/{task_id}/complete")
async def complete_task(task_id: int):
    """Mark a task as complete."""
    execute_query(
        "UPDATE Tasks SET Status = 'DONE', UpdatedAt = GETUTCDATE() WHERE TaskID = ?",
        (task_id,),
        fetch="none"
    )
    return {"message": "Task completed", "taskId": task_id}


@router.post("/{task_id}/reopen")
async def reopen_task(task_id: int):
    """Reopen a completed task."""
    execute_query(
        "UPDATE Tasks SET Status = 'STARTED', UpdatedAt = GETUTCDATE() WHERE TaskID = ?",
        (task_id,),
        fetch="none"
    )
    return {"message": "Task reopened", "taskId": task_id}

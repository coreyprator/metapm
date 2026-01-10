"""
MetaPM Tasks API
CRUD operations for tasks
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

from app.models.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
)
from app.core.database import execute_query, execute_procedure

router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, pattern="^(NEW|STARTED|BLOCKED|COMPLETE|CANCELLED)$"),
    priority: Optional[int] = Query(None, ge=1, le=5),
    project: Optional[str] = Query(None, description="Filter by project code"),
    category: Optional[str] = Query(None, description="Filter by category code"),
    overdue: Optional[bool] = Query(None, description="Show only overdue tasks"),
    no_due_date: Optional[bool] = Query(None, alias="noDueDate", description="Show tasks without due dates"),
    cross_project: Optional[bool] = Query(None, alias="crossProject", description="Show cross-project tasks only"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
):
    """
    List tasks with optional filters.
    """
    # Build dynamic WHERE clause
    conditions = ["1=1"]
    params = []
    
    if status:
        conditions.append("t.Status = ?")
        params.append(status)
    
    if priority:
        conditions.append("t.Priority = ?")
        params.append(priority)
    
    if overdue:
        conditions.append("t.DueDate < CAST(GETUTCDATE() AS DATE) AND t.Status NOT IN ('COMPLETE', 'CANCELLED')")
    
    if no_due_date:
        conditions.append("t.DueDate IS NULL AND t.Status NOT IN ('COMPLETE', 'CANCELLED')")
    
    where_clause = " AND ".join(conditions)
    
    # Project filter requires a join
    project_join = ""
    if project:
        project_join = """
            INNER JOIN TaskProjectLinks tpl_filter ON t.TaskID = tpl_filter.TaskID
            INNER JOIN Projects p_filter ON tpl_filter.ProjectID = p_filter.ProjectID AND p_filter.ProjectCode = ?
        """
        params.insert(0, project)  # Project param needs to come first for the join
    
    # Category filter
    category_join = ""
    if category:
        category_join = """
            INNER JOIN TaskCategoryLinks tcl_filter ON t.TaskID = tcl_filter.TaskID
            INNER JOIN Categories c_filter ON tcl_filter.CategoryID = c_filter.CategoryID AND c_filter.CategoryCode = ?
        """
        params.insert(0 if not project else 1, category)
    
    # Cross-project filter
    cross_project_having = ""
    if cross_project:
        cross_project_having = "HAVING COUNT(DISTINCT tpl.ProjectID) > 1"
    
    # Count query
    count_query = f"""
        SELECT COUNT(DISTINCT t.TaskID) as total
        FROM Tasks t
        {project_join}
        {category_join}
        WHERE {where_clause}
    """
    
    count_result = execute_query(count_query, tuple(params), fetch="one")
    total = count_result["total"] if count_result else 0
    
    # Main query with pagination
    offset = (page - 1) * page_size
    params_with_pagination = params + [page_size, offset]
    
    query = f"""
        SELECT 
            t.TaskID as taskId,
            t.Title as title,
            t.Description as description,
            t.ReferenceURL as referenceUrl,
            t.Priority as priority,
            t.Status as status,
            t.BlockedReason as blockedReason,
            t.Source as source,
            t.SprintNumber as sprintNumber,
            t.DueDate as dueDate,
            t.CreatedAt as createdAt,
            t.StartedAt as startedAt,
            t.CompletedAt as completedAt,
            t.UpdatedAt as updatedAt,
            (SELECT STRING_AGG(p2.ProjectCode, ',') 
             FROM TaskProjectLinks tpl2 
             JOIN Projects p2 ON tpl2.ProjectID = p2.ProjectID 
             WHERE tpl2.TaskID = t.TaskID) as projects,
            (SELECT STRING_AGG(c2.CategoryCode, ',') 
             FROM TaskCategoryLinks tcl2 
             JOIN Categories c2 ON tcl2.CategoryID = c2.CategoryID 
             WHERE tcl2.TaskID = t.TaskID) as categories,
            (SELECT p3.ProjectCode 
             FROM TaskProjectLinks tpl3 
             JOIN Projects p3 ON tpl3.ProjectID = p3.ProjectID 
             WHERE tpl3.TaskID = t.TaskID AND tpl3.IsPrimary = 1) as primaryProject
        FROM Tasks t
        {project_join}
        {category_join}
        WHERE {where_clause}
        ORDER BY t.Priority ASC, t.DueDate ASC, t.CreatedAt DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    
    rows = execute_query(query, tuple(params_with_pagination), fetch="all") or []
    
    # Transform rows to response format
    tasks = []
    for row in rows:
        task = dict(row)
        task["projects"] = row["projects"].split(",") if row.get("projects") else []
        task["categories"] = row["categories"].split(",") if row.get("categories") else []
        task["isCrossProject"] = len(task["projects"]) > 1
        tasks.append(TaskResponse(**task))
    
    return TaskListResponse(
        tasks=tasks,
        total=total,
        page=page,
        pageSize=page_size
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """Get a single task by ID"""
    query = """
        SELECT 
            t.TaskID as taskId,
            t.Title as title,
            t.Description as description,
            t.ReferenceURL as referenceUrl,
            t.Priority as priority,
            t.Status as status,
            t.BlockedReason as blockedReason,
            t.Source as source,
            t.SprintNumber as sprintNumber,
            t.DueDate as dueDate,
            t.CreatedAt as createdAt,
            t.StartedAt as startedAt,
            t.CompletedAt as completedAt,
            t.UpdatedAt as updatedAt,
            (SELECT STRING_AGG(p.ProjectCode, ',') 
             FROM TaskProjectLinks tpl 
             JOIN Projects p ON tpl.ProjectID = p.ProjectID 
             WHERE tpl.TaskID = t.TaskID) as projects,
            (SELECT STRING_AGG(c.CategoryCode, ',') 
             FROM TaskCategoryLinks tcl 
             JOIN Categories c ON tcl.CategoryID = c.CategoryID 
             WHERE tcl.TaskID = t.TaskID) as categories,
            (SELECT p.ProjectCode 
             FROM TaskProjectLinks tpl 
             JOIN Projects p ON tpl.ProjectID = p.ProjectID 
             WHERE tpl.TaskID = t.TaskID AND tpl.IsPrimary = 1) as primaryProject
        FROM Tasks t
        WHERE t.TaskID = ?
    """
    
    row = execute_query(query, (task_id,), fetch="one")
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = dict(row)
    task["projects"] = row["projects"].split(",") if row.get("projects") else []
    task["categories"] = row["categories"].split(",") if row.get("categories") else []
    task["isCrossProject"] = len(task["projects"]) > 1
    
    return TaskResponse(**task)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(task: TaskCreate):
    """Create a new task"""
    # Use stored procedure for atomic creation with links
    category_codes = ",".join(task.categories) if task.categories else None
    project_code = task.projects[0] if task.projects else None
    
    result = execute_procedure("sp_AddTask", {
        "Title": task.title,
        "Description": task.description,
        "ReferenceURL": task.reference_url,
        "Priority": task.priority,
        "DueDate": task.due_date,
        "ProjectCode": project_code,
        "CategoryCodes": category_codes,
        "Source": task.source
    })
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create task")
    
    new_task_id = result[0]["NewTaskID"]
    
    # Add additional project links if more than one project
    if task.projects and len(task.projects) > 1:
        for proj_code in task.projects[1:]:
            execute_query("""
                INSERT INTO TaskProjectLinks (TaskID, ProjectID, IsPrimary)
                SELECT ?, ProjectID, 0 FROM Projects WHERE ProjectCode = ?
            """, (new_task_id, proj_code), fetch="none")
    
    # Return the created task
    return await get_task(new_task_id)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task: TaskUpdate):
    """Update an existing task"""
    # Build dynamic UPDATE
    updates = []
    params = []
    
    if task.title is not None:
        updates.append("Title = ?")
        params.append(task.title)
    if task.description is not None:
        updates.append("Description = ?")
        params.append(task.description)
    if task.reference_url is not None:
        updates.append("ReferenceURL = ?")
        params.append(task.reference_url)
    if task.priority is not None:
        updates.append("Priority = ?")
        params.append(task.priority)
    if task.status is not None:
        updates.append("Status = ?")
        params.append(task.status)
        # Set timestamps based on status
        if task.status == "STARTED":
            updates.append("StartedAt = GETUTCDATE()")
        elif task.status == "COMPLETE":
            updates.append("CompletedAt = GETUTCDATE()")
    if task.blocked_reason is not None:
        updates.append("BlockedReason = ?")
        params.append(task.blocked_reason)
    if task.due_date is not None:
        updates.append("DueDate = ?")
        params.append(task.due_date)
    
    if updates:
        updates.append("UpdatedAt = GETUTCDATE()")
        params.append(task_id)
        
        query = f"UPDATE Tasks SET {', '.join(updates)} WHERE TaskID = ?"
        execute_query(query, tuple(params), fetch="none")
    
    # Update project links if provided
    if task.projects is not None:
        # Remove existing links
        execute_query("DELETE FROM TaskProjectLinks WHERE TaskID = ?", (task_id,), fetch="none")
        # Add new links
        for i, proj_code in enumerate(task.projects):
            execute_query("""
                INSERT INTO TaskProjectLinks (TaskID, ProjectID, IsPrimary)
                SELECT ?, ProjectID, ? FROM Projects WHERE ProjectCode = ?
            """, (task_id, 1 if i == 0 else 0, proj_code), fetch="none")
    
    # Update category links if provided
    if task.categories is not None:
        execute_query("DELETE FROM TaskCategoryLinks WHERE TaskID = ?", (task_id,), fetch="none")
        for cat_code in task.categories:
            execute_query("""
                INSERT INTO TaskCategoryLinks (TaskID, CategoryID)
                SELECT ?, CategoryID FROM Categories WHERE CategoryCode = ?
            """, (task_id, cat_code), fetch="none")
    
    return await get_task(task_id)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int):
    """Delete a task"""
    # Check exists
    existing = execute_query("SELECT TaskID FROM Tasks WHERE TaskID = ?", (task_id,), fetch="one")
    if not existing:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Delete (cascade will handle links)
    execute_query("DELETE FROM Tasks WHERE TaskID = ?", (task_id,), fetch="none")
    return None

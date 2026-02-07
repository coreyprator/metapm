"""
MetaPM Backlog API
==================

CRUD operations for:
- Bugs (defect tracking per project)
- Requirements (feature requests per project)
- Grouped backlog view (by project)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.core.database import execute_query

router = APIRouter()


# ============================================
# MODELS
# ============================================

class BugCreate(BaseModel):
    projectId: int
    code: str
    title: str
    description: Optional[str] = None
    status: Optional[str] = "Open"
    priority: Optional[str] = "P3"


class BugUpdate(BaseModel):
    projectId: Optional[int] = None
    code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class RequirementCreate(BaseModel):
    projectId: int
    code: str
    title: str
    description: Optional[str] = None
    referenceURL: Optional[str] = None
    status: Optional[str] = "Backlog"
    priority: Optional[str] = "P3"


class RequirementUpdate(BaseModel):
    projectId: Optional[int] = None
    code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    referenceURL: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


# ============================================
# BUGS ENDPOINTS
# ============================================

@router.get("/bugs")
async def list_bugs(
    project_id: Optional[int] = Query(None, alias="projectId"),
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    """List all bugs, optionally filtered."""
    query = """
        SELECT
            b.BugID as bugId,
            b.ProjectID as projectId,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            b.Code as code,
            b.Title as title,
            b.Description as description,
            b.Status as status,
            b.Priority as priority,
            b.ReportedDate as reportedDate,
            b.ResolvedDate as resolvedDate,
            b.CreatedAt as createdAt,
            b.UpdatedAt as updatedAt
        FROM Bugs b
        JOIN Projects p ON b.ProjectID = p.ProjectID
        WHERE 1=1
    """
    params = []

    if project_id is not None:
        query += " AND b.ProjectID = ?"
        params.append(project_id)
    if status:
        query += " AND b.Status = ?"
        params.append(status)
    if priority:
        query += " AND b.Priority = ?"
        params.append(priority)

    query += " ORDER BY b.Priority, b.ReportedDate DESC"

    bugs = execute_query(query, tuple(params) if params else None)
    return {"bugs": bugs, "count": len(bugs)}


@router.get("/bugs/{bug_id}")
async def get_bug(bug_id: int):
    """Get a single bug by ID."""
    query = """
        SELECT
            b.BugID as bugId,
            b.ProjectID as projectId,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            b.Code as code,
            b.Title as title,
            b.Description as description,
            b.Status as status,
            b.Priority as priority,
            b.ReportedDate as reportedDate,
            b.ResolvedDate as resolvedDate,
            b.CreatedAt as createdAt,
            b.UpdatedAt as updatedAt
        FROM Bugs b
        JOIN Projects p ON b.ProjectID = p.ProjectID
        WHERE b.BugID = ?
    """
    result = execute_query(query, (bug_id,), fetch="one")
    if not result:
        raise HTTPException(status_code=404, detail="Bug not found")
    return result


@router.post("/bugs")
async def create_bug(bug: BugCreate):
    """Create a new bug."""
    # Check for duplicate code within project
    existing = execute_query(
        "SELECT BugID FROM Bugs WHERE ProjectID = ? AND Code = ?",
        (bug.projectId, bug.code),
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Bug code {bug.code} already exists for this project")

    query = """
        INSERT INTO Bugs (ProjectID, Code, Title, Description, Status, Priority)
        OUTPUT INSERTED.BugID as bugId, INSERTED.Code as code, INSERTED.Title as title
        VALUES (?, ?, ?, ?, ?, ?)
    """
    result = execute_query(
        query,
        (bug.projectId, bug.code, bug.title, bug.description, bug.status, bug.priority),
        fetch="one"
    )
    return {"message": "Bug created", "bug": result}


@router.put("/bugs/{bug_id}")
async def update_bug(bug_id: int, bug: BugUpdate):
    """Update a bug."""
    updates = []
    params = []

    if bug.projectId is not None:
        updates.append("ProjectID = ?")
        params.append(bug.projectId)
    if bug.code is not None:
        updates.append("Code = ?")
        params.append(bug.code)
    if bug.title is not None:
        updates.append("Title = ?")
        params.append(bug.title)
    if bug.description is not None:
        updates.append("Description = ?")
        params.append(bug.description)
    if bug.status is not None:
        updates.append("Status = ?")
        params.append(bug.status)
        # Auto-set ResolvedDate when status becomes Fixed or Closed
        if bug.status in ("Fixed", "Closed"):
            updates.append("ResolvedDate = GETUTCDATE()")
        elif bug.status in ("Open", "In Progress"):
            updates.append("ResolvedDate = NULL")
    if bug.priority is not None:
        updates.append("Priority = ?")
        params.append(bug.priority)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("UpdatedAt = GETUTCDATE()")
    params.append(bug_id)

    query = f"UPDATE Bugs SET {', '.join(updates)} WHERE BugID = ?"
    execute_query(query, tuple(params), fetch="none")
    return {"message": "Bug updated", "bugId": bug_id}


@router.delete("/bugs/{bug_id}")
async def delete_bug(bug_id: int):
    """Delete a bug."""
    execute_query("DELETE FROM Bugs WHERE BugID = ?", (bug_id,), fetch="none")
    return {"message": "Bug deleted"}


# ============================================
# REQUIREMENTS ENDPOINTS
# ============================================

@router.get("/requirements")
async def list_requirements(
    project_id: Optional[int] = Query(None, alias="projectId"),
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    """List all requirements, optionally filtered."""
    query = """
        SELECT
            r.RequirementID as requirementId,
            r.ProjectID as projectId,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            r.Code as code,
            r.Title as title,
            r.Description as description,
            r.ReferenceURL as referenceURL,
            r.Status as status,
            r.Priority as priority,
            r.CreatedAt as createdAt,
            r.UpdatedAt as updatedAt
        FROM Requirements r
        JOIN Projects p ON r.ProjectID = p.ProjectID
        WHERE 1=1
    """
    params = []

    if project_id is not None:
        query += " AND r.ProjectID = ?"
        params.append(project_id)
    if status:
        query += " AND r.Status = ?"
        params.append(status)
    if priority:
        query += " AND r.Priority = ?"
        params.append(priority)

    query += " ORDER BY r.Priority, r.CreatedAt DESC"

    reqs = execute_query(query, tuple(params) if params else None)
    return {"requirements": reqs, "count": len(reqs)}


@router.get("/requirements/{req_id}")
async def get_requirement(req_id: int):
    """Get a single requirement by ID."""
    query = """
        SELECT
            r.RequirementID as requirementId,
            r.ProjectID as projectId,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            r.Code as code,
            r.Title as title,
            r.Description as description,
            r.ReferenceURL as referenceURL,
            r.Status as status,
            r.Priority as priority,
            r.CreatedAt as createdAt,
            r.UpdatedAt as updatedAt
        FROM Requirements r
        JOIN Projects p ON r.ProjectID = p.ProjectID
        WHERE r.RequirementID = ?
    """
    result = execute_query(query, (req_id,), fetch="one")
    if not result:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return result


@router.post("/requirements")
async def create_requirement(req: RequirementCreate):
    """Create a new requirement."""
    existing = execute_query(
        "SELECT RequirementID FROM Requirements WHERE ProjectID = ? AND Code = ?",
        (req.projectId, req.code),
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Requirement code {req.code} already exists for this project")

    query = """
        INSERT INTO Requirements (ProjectID, Code, Title, Description, ReferenceURL, Status, Priority)
        OUTPUT INSERTED.RequirementID as requirementId, INSERTED.Code as code, INSERTED.Title as title
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    result = execute_query(
        query,
        (req.projectId, req.code, req.title, req.description, req.referenceURL, req.status, req.priority),
        fetch="one"
    )
    return {"message": "Requirement created", "requirement": result}


@router.put("/requirements/{req_id}")
async def update_requirement(req_id: int, req: RequirementUpdate):
    """Update a requirement."""
    updates = []
    params = []

    if req.projectId is not None:
        updates.append("ProjectID = ?")
        params.append(req.projectId)
    if req.code is not None:
        updates.append("Code = ?")
        params.append(req.code)
    if req.title is not None:
        updates.append("Title = ?")
        params.append(req.title)
    if req.description is not None:
        updates.append("Description = ?")
        params.append(req.description)
    if req.referenceURL is not None:
        updates.append("ReferenceURL = ?")
        params.append(req.referenceURL)
    if req.status is not None:
        updates.append("Status = ?")
        params.append(req.status)
    if req.priority is not None:
        updates.append("Priority = ?")
        params.append(req.priority)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("UpdatedAt = GETUTCDATE()")
    params.append(req_id)

    query = f"UPDATE Requirements SET {', '.join(updates)} WHERE RequirementID = ?"
    execute_query(query, tuple(params), fetch="none")
    return {"message": "Requirement updated", "requirementId": req_id}


@router.delete("/requirements/{req_id}")
async def delete_requirement(req_id: int):
    """Delete a requirement."""
    execute_query("DELETE FROM Requirements WHERE RequirementID = ?", (req_id,), fetch="none")
    return {"message": "Requirement deleted"}


# ============================================
# GROUPED BACKLOG VIEW
# ============================================

@router.get("/grouped")
async def get_grouped_backlog():
    """Get all bugs and requirements grouped by project."""
    bugs = execute_query("""
        SELECT
            b.BugID as bugId,
            b.ProjectID as projectId,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            b.Code as code,
            b.Title as title,
            b.Status as status,
            b.Priority as priority,
            b.ReportedDate as reportedDate,
            b.ResolvedDate as resolvedDate
        FROM Bugs b
        JOIN Projects p ON b.ProjectID = p.ProjectID
        ORDER BY p.ProjectName, b.Priority, b.Code
    """)

    reqs = execute_query("""
        SELECT
            r.RequirementID as requirementId,
            r.ProjectID as projectId,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            r.Code as code,
            r.Title as title,
            r.Status as status,
            r.Priority as priority,
            r.CreatedAt as createdAt
        FROM Requirements r
        JOIN Projects p ON r.ProjectID = p.ProjectID
        ORDER BY p.ProjectName, r.Priority, r.Code
    """)

    # Group by project
    projects = {}
    for bug in bugs:
        pid = bug['projectId']
        if pid not in projects:
            projects[pid] = {
                'projectId': pid,
                'projectCode': bug['projectCode'],
                'projectName': bug['projectName'],
                'bugs': [],
                'requirements': []
            }
        projects[pid]['bugs'].append(bug)

    for req in reqs:
        pid = req['projectId']
        if pid not in projects:
            projects[pid] = {
                'projectId': pid,
                'projectCode': req['projectCode'],
                'projectName': req['projectName'],
                'bugs': [],
                'requirements': []
            }
        projects[pid]['requirements'].append(req)

    return {
        "projects": list(projects.values()),
        "totalBugs": len(bugs),
        "totalRequirements": len(reqs)
    }


# ============================================
# NEXT CODE GENERATOR
# ============================================

@router.get("/next-code/{project_id}/{item_type}")
async def get_next_code(project_id: int, item_type: str):
    """Get the next available code for a bug or requirement in a project."""
    if item_type not in ("bug", "requirement"):
        raise HTTPException(status_code=400, detail="item_type must be 'bug' or 'requirement'")

    if item_type == "bug":
        result = execute_query(
            "SELECT MAX(CAST(REPLACE(Code, 'BUG-', '') AS INT)) as maxNum FROM Bugs WHERE ProjectID = ?",
            (project_id,),
            fetch="one"
        )
        next_num = (result['maxNum'] or 0) + 1 if result else 1
        return {"code": f"BUG-{next_num:03d}"}
    else:
        result = execute_query(
            "SELECT MAX(CAST(REPLACE(Code, 'REQ-', '') AS INT)) as maxNum FROM Requirements WHERE ProjectID = ?",
            (project_id,),
            fetch="one"
        )
        next_num = (result['maxNum'] or 0) + 1 if result else 1
        return {"code": f"REQ-{next_num:03d}"}

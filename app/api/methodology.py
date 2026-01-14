"""
MetaPM Methodology API
======================

CRUD operations for:
- MethodologyRules (lessons learned)
- MethodologyViolations (tracked violations)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.database import execute_query, execute_procedure

router = APIRouter()


# ============================================
# MODELS
# ============================================

class RuleCreate(BaseModel):
    ruleCode: str
    ruleName: str
    description: str
    category: Optional[str] = "DEVELOPMENT"
    severity: Optional[str] = "MEDIUM"


class RuleUpdate(BaseModel):
    ruleCode: Optional[str] = None
    ruleName: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    isActive: Optional[bool] = None


class ViolationCreate(BaseModel):
    ruleId: int
    projectId: int
    context: Optional[str] = None
    copilotSessionRef: Optional[str] = None
    resolution: Optional[str] = None


# ============================================
# RULES ENDPOINTS
# ============================================

@router.get("/rules")
async def list_rules(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    active_only: bool = True
):
    """List all methodology rules."""
    query = """
        SELECT 
            RuleID as ruleId,
            RuleCode as ruleCode,
            RuleName as ruleName,
            Description as description,
            Category as category,
            Severity as severity,
            IsActive as isActive
        FROM MethodologyRules
        WHERE 1=1
    """
    
    if active_only:
        query += " AND IsActive = 1"
    if category:
        query += f" AND Category = '{category}'"
    if severity:
        query += f" AND Severity = '{severity}'"
    
    query += " ORDER BY RuleCode"
    
    rules = execute_query(query)
    return {"rules": rules, "count": len(rules)}


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: int):
    """Get a specific rule by ID."""
    query = """
        SELECT 
            RuleID as ruleId,
            RuleCode as ruleCode,
            RuleName as ruleName,
            Description as description,
            Category as category,
            Severity as severity,
            IsActive as isActive
        FROM MethodologyRules
        WHERE RuleID = ?
    """
    
    result = execute_query(query, (rule_id,), fetch="one")
    if not result:
        raise HTTPException(status_code=404, detail="Rule not found")
    return result


@router.post("/rules")
async def create_rule(rule: RuleCreate):
    """Create a new methodology rule."""
    # Check for duplicate code
    existing = execute_query(
        "SELECT RuleID FROM MethodologyRules WHERE RuleCode = ?",
        (rule.ruleCode,),
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Rule code {rule.ruleCode} already exists")
    
    query = """
        INSERT INTO MethodologyRules (RuleCode, RuleName, Description, Category, Severity)
        OUTPUT INSERTED.RuleID, INSERTED.RuleCode, INSERTED.RuleName
        VALUES (?, ?, ?, ?, ?)
    """
    
    result = execute_query(
        query,
        (rule.ruleCode, rule.ruleName, rule.description, rule.category, rule.severity),
        fetch="one"
    )
    
    return {"message": "Rule created", "rule": result}


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, rule: RuleUpdate):
    """Update a methodology rule."""
    # Build dynamic update
    updates = []
    params = []
    
    if rule.ruleCode is not None:
        updates.append("RuleCode = ?")
        params.append(rule.ruleCode)
    if rule.ruleName is not None:
        updates.append("RuleName = ?")
        params.append(rule.ruleName)
    if rule.description is not None:
        updates.append("Description = ?")
        params.append(rule.description)
    if rule.category is not None:
        updates.append("Category = ?")
        params.append(rule.category)
    if rule.severity is not None:
        updates.append("Severity = ?")
        params.append(rule.severity)
    if rule.isActive is not None:
        updates.append("IsActive = ?")
        params.append(1 if rule.isActive else 0)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("UpdatedAt = GETUTCDATE()")
    params.append(rule_id)
    
    query = f"UPDATE MethodologyRules SET {', '.join(updates)} WHERE RuleID = ?"
    execute_query(query, tuple(params), fetch="none")
    
    return {"message": "Rule updated", "ruleId": rule_id}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, hard_delete: bool = False):
    """Delete a methodology rule (soft delete by default)."""
    if hard_delete:
        execute_query("DELETE FROM MethodologyRules WHERE RuleID = ?", (rule_id,), fetch="none")
        return {"message": "Rule permanently deleted"}
    else:
        execute_query(
            "UPDATE MethodologyRules SET IsActive = 0, UpdatedAt = GETUTCDATE() WHERE RuleID = ?",
            (rule_id,),
            fetch="none"
        )
        return {"message": "Rule deactivated"}


# ============================================
# VIOLATIONS ENDPOINTS
# ============================================

@router.get("/violations")
async def list_violations(
    project_id: Optional[int] = None,
    rule_id: Optional[int] = None,
    resolved: Optional[bool] = None,
    limit: int = Query(default=50, le=200)
):
    """List methodology violations."""
    query = """
        SELECT 
            v.ViolationID as violationId,
            v.RuleID as ruleId,
            r.RuleCode as ruleCode,
            r.RuleName as ruleName,
            v.ProjectID as projectId,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            v.Context as context,
            v.CreatedAt as createdAt
        FROM MethodologyViolations v
        JOIN MethodologyRules r ON v.RuleID = r.RuleID
        LEFT JOIN Projects p ON v.ProjectID = p.ProjectID
        WHERE 1=1
    """
    
    if project_id:
        query += f" AND v.ProjectID = {project_id}"
    if rule_id:
        query += f" AND v.RuleID = {rule_id}"
    # Note: resolved parameter ignored until Resolution column added to schema
    
    query += f" ORDER BY v.CreatedAt DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
    
    violations = execute_query(query)
    return {"violations": violations, "count": len(violations)}


@router.get("/violations/by-project/{project_code}")
async def get_violations_by_project(project_code: str):
    """Get all violations for a project."""
    query = """
        SELECT 
            v.ViolationID as violationId,
            v.RuleID as ruleId,
            r.RuleCode as ruleCode,
            r.RuleName as ruleName,
            v.Context as context,
            v.CopilotSessionRef as copilotSessionRef,
            v.Resolution as resolution,
            v.ResolvedAt as resolvedAt,
            v.CreatedAt as createdAt
        FROM MethodologyViolations v
        JOIN MethodologyRules r ON v.RuleID = r.RuleID
        JOIN Projects p ON v.ProjectID = p.ProjectID
        WHERE p.ProjectCode = ?
        ORDER BY v.CreatedAt DESC
    """
    
    violations = execute_query(query, (project_code,))
    return {"projectCode": project_code, "violations": violations, "count": len(violations)}


@router.post("/violations")
async def create_violation(violation: ViolationCreate):
    """Log a new methodology violation."""
    query = """
        INSERT INTO MethodologyViolations (RuleID, ProjectID, Context, CopilotSessionRef, Resolution)
        OUTPUT INSERTED.ViolationID
        VALUES (?, ?, ?, ?, ?)
    """
    
    result = execute_query(
        query,
        (violation.ruleId, violation.projectId, violation.context, violation.copilotSessionRef, violation.resolution),
        fetch="one"
    )
    
    # If resolution provided, set resolved timestamp
    if violation.resolution:
        execute_query(
            "UPDATE MethodologyViolations SET ResolvedAt = GETUTCDATE() WHERE ViolationID = ?",
            (result['ViolationID'],),
            fetch="none"
        )
    
    return {"message": "Violation logged", "violationId": result['ViolationID']}


@router.put("/violations/{violation_id}/resolve")
async def resolve_violation(violation_id: int, resolution: str):
    """Mark a violation as resolved."""
    execute_query(
        "UPDATE MethodologyViolations SET Resolution = ?, ResolvedAt = GETUTCDATE() WHERE ViolationID = ?",
        (resolution, violation_id),
        fetch="none"
    )
    return {"message": "Violation resolved", "violationId": violation_id}


@router.delete("/violations/{violation_id}")
async def delete_violation(violation_id: int):
    """Delete a violation record."""
    execute_query("DELETE FROM MethodologyViolations WHERE ViolationID = ?", (violation_id,), fetch="none")
    return {"message": "Violation deleted"}


# ============================================
# ANALYTICS
# ============================================

@router.get("/analytics")
async def methodology_analytics():
    """Get methodology analytics."""
    # Violations by rule
    by_rule = execute_query("""
        SELECT r.RuleCode, r.RuleName, COUNT(*) as violationCount
        FROM MethodologyViolations v
        JOIN MethodologyRules r ON v.RuleID = r.RuleID
        GROUP BY r.RuleID, r.RuleCode, r.RuleName
        ORDER BY violationCount DESC
    """)
    
    # Violations by project
    by_project = execute_query("""
        SELECT p.ProjectCode, p.ProjectName, COUNT(*) as violationCount
        FROM MethodologyViolations v
        JOIN Projects p ON v.ProjectID = p.ProjectID
        GROUP BY p.ProjectID, p.ProjectCode, p.ProjectName
        ORDER BY violationCount DESC
    """)
    
    # Resolution rate
    stats = execute_query("""
        SELECT 
            COUNT(*) as totalViolations,
            SUM(CASE WHEN Resolution IS NOT NULL THEN 1 ELSE 0 END) as resolvedCount,
            AVG(CASE WHEN Resolution IS NOT NULL THEN DATEDIFF(HOUR, CreatedAt, ResolvedAt) END) as avgResolutionHours
        FROM MethodologyViolations
    """, fetch="one")
    
    return {
        "byRule": by_rule,
        "byProject": by_project,
        "stats": stats
    }

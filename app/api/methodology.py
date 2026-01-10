"""
MetaPM Methodology API
Methodology rules and violation tracking
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.methodology import (
    MethodologyRuleCreate, MethodologyRuleUpdate, MethodologyRuleResponse,
    MethodologyRuleListResponse, ViolationCreate, ViolationResponse,
    ViolationListResponse, ViolationSummary, ViolationSummaryResponse
)
from app.core.database import execute_query

router = APIRouter()


# ============================================
# RULES ENDPOINTS
# ============================================

@router.get("/rules", response_model=MethodologyRuleListResponse)
async def list_rules(
    category: Optional[str] = Query(None, description="Filter by category"),
    severity: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    active_only: bool = Query(True, alias="activeOnly"),
):
    """List all methodology rules"""
    conditions = []
    params = []
    
    if category:
        conditions.append("mr.Category = ?")
        params.append(category)
    
    if severity:
        conditions.append("mr.Severity = ?")
        params.append(severity)
    
    if active_only:
        conditions.append("mr.IsActive = 1")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT 
            mr.RuleID as ruleId,
            mr.RuleCode as ruleCode,
            mr.RuleName as ruleName,
            mr.Category as category,
            mr.Description as description,
            mr.ViolationPrompt as violationPrompt,
            mr.Severity as severity,
            mr.IsActive as isActive,
            mr.CreatedAt as createdAt,
            (SELECT COUNT(*) FROM MethodologyViolations mv WHERE mv.RuleID = mr.RuleID) as totalViolations,
            (SELECT COUNT(*) FROM MethodologyViolations mv WHERE mv.RuleID = mr.RuleID AND mv.ResolvedAt IS NULL) as openViolations
        FROM MethodologyRules mr
        WHERE {where_clause}
        ORDER BY 
            CASE mr.Severity 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                WHEN 'LOW' THEN 4 
            END,
            mr.RuleName
    """
    
    rows = execute_query(query, tuple(params) if params else None, fetch="all") or []
    rules = [MethodologyRuleResponse(**row) for row in rows]
    
    return MethodologyRuleListResponse(rules=rules, total=len(rules))


@router.get("/rules/{rule_code}", response_model=MethodologyRuleResponse)
async def get_rule(rule_code: str):
    """
    Get a single rule with its violation prompt.
    
    Use this to get the pre-written prompt to paste into VS Code Copilot
    when a methodology violation occurs.
    """
    query = """
        SELECT 
            mr.RuleID as ruleId,
            mr.RuleCode as ruleCode,
            mr.RuleName as ruleName,
            mr.Category as category,
            mr.Description as description,
            mr.ViolationPrompt as violationPrompt,
            mr.Severity as severity,
            mr.IsActive as isActive,
            mr.CreatedAt as createdAt,
            (SELECT COUNT(*) FROM MethodologyViolations mv WHERE mv.RuleID = mr.RuleID) as totalViolations,
            (SELECT COUNT(*) FROM MethodologyViolations mv WHERE mv.RuleID = mr.RuleID AND mv.ResolvedAt IS NULL) as openViolations
        FROM MethodologyRules mr
        WHERE mr.RuleCode = ?
    """
    
    row = execute_query(query, (rule_code,), fetch="one")
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Rule {rule_code} not found")
    
    return MethodologyRuleResponse(**row)


@router.post("/rules", response_model=MethodologyRuleResponse, status_code=201)
async def create_rule(rule: MethodologyRuleCreate):
    """Create a new methodology rule"""
    existing = execute_query(
        "SELECT RuleID FROM MethodologyRules WHERE RuleCode = ?",
        (rule.rule_code,),
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Rule code {rule.rule_code} already exists")
    
    query = """
        INSERT INTO MethodologyRules (RuleCode, RuleName, Category, Description, ViolationPrompt, Severity, IsActive)
        OUTPUT INSERTED.RuleID
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    
    result = execute_query(query, (
        rule.rule_code,
        rule.rule_name,
        rule.category,
        rule.description,
        rule.violation_prompt,
        rule.severity,
        1 if rule.is_active else 0
    ), fetch="one")
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create rule")
    
    return await get_rule(rule.rule_code)


@router.put("/rules/{rule_code}", response_model=MethodologyRuleResponse)
async def update_rule(rule_code: str, rule: MethodologyRuleUpdate):
    """Update a methodology rule"""
    existing = execute_query(
        "SELECT RuleID FROM MethodologyRules WHERE RuleCode = ?",
        (rule_code,),
        fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"Rule {rule_code} not found")
    
    updates = []
    params = []
    
    if rule.rule_name is not None:
        updates.append("RuleName = ?")
        params.append(rule.rule_name)
    if rule.category is not None:
        updates.append("Category = ?")
        params.append(rule.category)
    if rule.description is not None:
        updates.append("Description = ?")
        params.append(rule.description)
    if rule.violation_prompt is not None:
        updates.append("ViolationPrompt = ?")
        params.append(rule.violation_prompt)
    if rule.severity is not None:
        updates.append("Severity = ?")
        params.append(rule.severity)
    if rule.is_active is not None:
        updates.append("IsActive = ?")
        params.append(1 if rule.is_active else 0)
    
    if updates:
        params.append(rule_code)
        query = f"UPDATE MethodologyRules SET {', '.join(updates)} WHERE RuleCode = ?"
        execute_query(query, tuple(params), fetch="none")
    
    return await get_rule(rule_code)


# ============================================
# VIOLATIONS ENDPOINTS
# ============================================

@router.get("/violations", response_model=ViolationListResponse)
async def list_violations(
    project: Optional[str] = Query(None, description="Filter by project code"),
    rule: Optional[str] = Query(None, description="Filter by rule code"),
    open_only: bool = Query(False, alias="openOnly"),
    limit: int = Query(50, ge=1, le=200),
):
    """List methodology violations"""
    conditions = []
    params = []
    
    if project:
        conditions.append("p.ProjectCode = ?")
        params.append(project)
    
    if rule:
        conditions.append("mr.RuleCode = ?")
        params.append(rule)
    
    if open_only:
        conditions.append("mv.ResolvedAt IS NULL")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT TOP (?)
            mv.ViolationID as violationId,
            mr.RuleCode as ruleCode,
            mr.RuleName as ruleName,
            p.ProjectCode as projectCode,
            mv.TaskID as taskId,
            mv.Description as description,
            mv.CopilotSessionRef as copilotSessionRef,
            mv.Resolution as resolution,
            mv.CreatedAt as createdAt,
            mv.ResolvedAt as resolvedAt
        FROM MethodologyViolations mv
        JOIN MethodologyRules mr ON mv.RuleID = mr.RuleID
        LEFT JOIN Projects p ON mv.ProjectID = p.ProjectID
        WHERE {where_clause}
        ORDER BY mv.CreatedAt DESC
    """
    
    all_params = [limit] + params
    rows = execute_query(query, tuple(all_params), fetch="all") or []
    violations = [ViolationResponse(**row) for row in rows]
    
    return ViolationListResponse(violations=violations, total=len(violations))


@router.post("/violations", response_model=ViolationResponse, status_code=201)
async def log_violation(violation: ViolationCreate):
    """Log a methodology violation"""
    # Verify rule exists
    rule = execute_query(
        "SELECT RuleID FROM MethodologyRules WHERE RuleCode = ?",
        (violation.rule_code,),
        fetch="one"
    )
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {violation.rule_code} not found")
    
    # Verify project exists
    project = execute_query(
        "SELECT ProjectID FROM Projects WHERE ProjectCode = ?",
        (violation.project_code,),
        fetch="one"
    )
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {violation.project_code} not found")
    
    query = """
        INSERT INTO MethodologyViolations (RuleID, ProjectID, TaskID, Description, CopilotSessionRef)
        OUTPUT INSERTED.ViolationID
        VALUES (?, ?, ?, ?, ?)
    """
    
    result = execute_query(query, (
        rule["RuleID"],
        project["ProjectID"],
        violation.task_id,
        violation.description,
        violation.copilot_session_ref
    ), fetch="one")
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to log violation")
    
    # Fetch and return
    return await get_violation(result["ViolationID"])


async def get_violation(violation_id: int) -> ViolationResponse:
    """Get a single violation"""
    query = """
        SELECT 
            mv.ViolationID as violationId,
            mr.RuleCode as ruleCode,
            mr.RuleName as ruleName,
            p.ProjectCode as projectCode,
            mv.TaskID as taskId,
            mv.Description as description,
            mv.CopilotSessionRef as copilotSessionRef,
            mv.Resolution as resolution,
            mv.CreatedAt as createdAt,
            mv.ResolvedAt as resolvedAt
        FROM MethodologyViolations mv
        JOIN MethodologyRules mr ON mv.RuleID = mr.RuleID
        LEFT JOIN Projects p ON mv.ProjectID = p.ProjectID
        WHERE mv.ViolationID = ?
    """
    
    row = execute_query(query, (violation_id,), fetch="one")
    if not row:
        raise HTTPException(status_code=404, detail=f"Violation {violation_id} not found")
    
    return ViolationResponse(**row)


@router.put("/violations/{violation_id}/resolve")
async def resolve_violation(violation_id: int, resolution: str):
    """Mark a violation as resolved"""
    existing = execute_query(
        "SELECT ViolationID FROM MethodologyViolations WHERE ViolationID = ?",
        (violation_id,),
        fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"Violation {violation_id} not found")
    
    execute_query("""
        UPDATE MethodologyViolations 
        SET Resolution = ?, ResolvedAt = GETUTCDATE()
        WHERE ViolationID = ?
    """, (resolution, violation_id), fetch="none")
    
    return await get_violation(violation_id)


@router.get("/violations/summary", response_model=ViolationSummaryResponse)
async def get_violation_summary():
    """Get violation statistics by rule"""
    query = """
        SELECT 
            mr.RuleCode as ruleCode,
            mr.RuleName as ruleName,
            mr.Severity as severity,
            COUNT(mv.ViolationID) as totalViolations,
            SUM(CASE WHEN mv.ResolvedAt IS NULL THEN 1 ELSE 0 END) as openViolations,
            MAX(mv.CreatedAt) as lastViolation
        FROM MethodologyRules mr
        LEFT JOIN MethodologyViolations mv ON mr.RuleID = mv.RuleID
        GROUP BY mr.RuleCode, mr.RuleName, mr.Severity
        ORDER BY 
            CASE mr.Severity 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                WHEN 'LOW' THEN 4 
            END,
            totalViolations DESC
    """
    
    rows = execute_query(query, fetch="all") or []
    summaries = [ViolationSummary(**row) for row in rows]
    
    total_open = sum(s.open_violations for s in summaries)
    total_all = sum(s.total_violations for s in summaries)
    
    return ViolationSummaryResponse(
        summaries=summaries,
        totalOpen=total_open,
        totalAllTime=total_all
    )

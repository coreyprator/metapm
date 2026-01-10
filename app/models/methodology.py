"""
MetaPM Methodology Models
Pydantic models for methodology rules and violation tracking
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MethodologyRuleBase(BaseModel):
    """Base methodology rule fields"""
    rule_code: str = Field(..., alias="ruleCode", max_length=50)
    rule_name: str = Field(..., alias="ruleName", max_length=200)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    violation_prompt: Optional[str] = Field(None, alias="violationPrompt")
    severity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")


class MethodologyRuleCreate(MethodologyRuleBase):
    """Fields for creating a new rule"""
    is_active: bool = Field(default=True, alias="isActive")
    
    class Config:
        populate_by_name = True


class MethodologyRuleUpdate(BaseModel):
    """Fields for updating a rule (all optional)"""
    rule_name: Optional[str] = Field(None, alias="ruleName", max_length=200)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    violation_prompt: Optional[str] = Field(None, alias="violationPrompt")
    severity: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    is_active: Optional[bool] = Field(None, alias="isActive")
    
    class Config:
        populate_by_name = True


class MethodologyRuleResponse(MethodologyRuleBase):
    """Full rule response"""
    rule_id: int = Field(..., alias="ruleId")
    is_active: bool = Field(..., alias="isActive")
    created_at: datetime = Field(..., alias="createdAt")
    
    # Computed
    total_violations: int = Field(default=0, alias="totalViolations")
    open_violations: int = Field(default=0, alias="openViolations")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class ViolationCreate(BaseModel):
    """Log a methodology violation"""
    rule_code: str = Field(..., alias="ruleCode")
    project_code: str = Field(..., alias="projectCode")
    task_id: Optional[int] = Field(None, alias="taskId")
    description: str
    copilot_session_ref: Optional[str] = Field(None, alias="copilotSessionRef", max_length=500)
    
    class Config:
        populate_by_name = True


class ViolationResponse(BaseModel):
    """Violation details"""
    violation_id: int = Field(..., alias="violationId")
    rule_code: str = Field(..., alias="ruleCode")
    rule_name: str = Field(..., alias="ruleName")
    project_code: str = Field(..., alias="projectCode")
    task_id: Optional[int] = Field(None, alias="taskId")
    description: str
    copilot_session_ref: Optional[str] = Field(None, alias="copilotSessionRef")
    resolution: Optional[str] = None
    created_at: datetime = Field(..., alias="createdAt")
    resolved_at: Optional[datetime] = Field(None, alias="resolvedAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class ViolationSummary(BaseModel):
    """Summary statistics for violations"""
    rule_code: str = Field(..., alias="ruleCode")
    rule_name: str = Field(..., alias="ruleName")
    severity: str
    total_violations: int = Field(..., alias="totalViolations")
    open_violations: int = Field(..., alias="openViolations")
    last_violation: Optional[datetime] = Field(None, alias="lastViolation")
    
    class Config:
        populate_by_name = True


class MethodologyRuleListResponse(BaseModel):
    """List of methodology rules"""
    rules: List[MethodologyRuleResponse]
    total: int


class ViolationListResponse(BaseModel):
    """List of violations"""
    violations: List[ViolationResponse]
    total: int


class ViolationSummaryResponse(BaseModel):
    """Violation summary statistics"""
    summaries: List[ViolationSummary]
    total_open: int = Field(..., alias="totalOpen")
    total_all_time: int = Field(..., alias="totalAllTime")
    
    class Config:
        populate_by_name = True

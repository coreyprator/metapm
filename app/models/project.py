"""
MetaPM Project Models
Pydantic models for project-related data
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base project fields"""
    project_code: str = Field(..., alias="projectCode", max_length=20)
    project_name: str = Field(..., alias="projectName", max_length=200)
    theme: Optional[str] = None
    description: Optional[str] = None
    project_url: Optional[str] = Field(None, alias="projectUrl", max_length=500)
    github_repo: Optional[str] = Field(None, alias="githubRepo", max_length=500)
    vscode_workspace: Optional[str] = Field(None, alias="vscodeWorkspace", max_length=500)


class ProjectCreate(ProjectBase):
    """Fields for creating a new project"""
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|PAUSED|COMPLETED|ARCHIVED|BLOCKED|NOT_STARTED)$")
    priority: int = Field(default=3, ge=1, le=5)
    
    class Config:
        populate_by_name = True


class ProjectUpdate(BaseModel):
    """Fields for updating a project (all optional)"""
    project_name: Optional[str] = Field(None, alias="projectName", max_length=200)
    theme: Optional[str] = None
    description: Optional[str] = None
    project_url: Optional[str] = Field(None, alias="projectUrl", max_length=500)
    github_repo: Optional[str] = Field(None, alias="githubRepo", max_length=500)
    vscode_workspace: Optional[str] = Field(None, alias="vscodeWorkspace", max_length=500)
    status: Optional[str] = Field(None, pattern="^(ACTIVE|PAUSED|COMPLETED|ARCHIVED|BLOCKED|NOT_STARTED)$")
    priority: Optional[int] = Field(None, ge=1, le=5)
    
    class Config:
        populate_by_name = True


class ProjectResponse(ProjectBase):
    """Full project response"""
    project_id: int = Field(..., alias="projectId")
    status: str
    priority: int
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    
    # Computed/aggregated
    task_count: int = Field(default=0, alias="taskCount")
    open_task_count: int = Field(default=0, alias="openTaskCount")
    blocked_task_count: int = Field(default=0, alias="blockedTaskCount")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """Project with related tasks"""
    tasks: List["TaskSummary"] = Field(default_factory=list)
    linked_projects: List[str] = Field(default_factory=list, alias="linkedProjects")
    
    class Config:
        populate_by_name = True


class TaskSummary(BaseModel):
    """Minimal task info for embedding in project response"""
    task_id: int = Field(..., alias="taskId")
    title: str
    priority: int
    status: str
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    categories: List[str] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True


class ProjectListResponse(BaseModel):
    """List of projects"""
    projects: List[ProjectResponse]
    total: int
    
    class Config:
        populate_by_name = True


class CrossProjectLinkCreate(BaseModel):
    """Create a link between projects"""
    source_project: str = Field(..., alias="sourceProject")
    target_project: str = Field(..., alias="targetProject")
    link_type: str = Field(..., alias="linkType", pattern="^(SHARES_CODE|SHARES_DATA|SHARES_CONCEPT|DEPENDS_ON)$")
    description: Optional[str] = None
    
    class Config:
        populate_by_name = True


# Update forward reference
ProjectDetailResponse.model_rebuild()

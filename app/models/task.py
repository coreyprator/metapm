"""
MetaPM Task Models
Pydantic models for task-related data
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """Base task fields"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    reference_url: Optional[str] = Field(None, alias="referenceUrl", max_length=1000)
    priority: int = Field(default=3, ge=1, le=5)
    due_date: Optional[date] = Field(None, alias="dueDate")
    

class TaskCreate(TaskBase):
    """Fields for creating a new task"""
    projects: Optional[List[str]] = Field(default=None, description="List of project codes")
    categories: Optional[List[str]] = Field(default=None, description="List of category codes")
    sprint_number: Optional[int] = Field(None, alias="sprintNumber")
    source: str = Field(default="MANUAL")
    
    class Config:
        populate_by_name = True


class TaskUpdate(BaseModel):
    """Fields for updating a task (all optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    reference_url: Optional[str] = Field(None, alias="referenceUrl", max_length=1000)
    priority: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[str] = Field(None, pattern="^(NEW|STARTED|BLOCKED|COMPLETE|CANCELLED)$")
    blocked_reason: Optional[str] = Field(None, alias="blockedReason", max_length=500)
    due_date: Optional[date] = Field(None, alias="dueDate")
    projects: Optional[List[str]] = Field(None, description="Replace project links")
    categories: Optional[List[str]] = Field(None, description="Replace category links")
    
    class Config:
        populate_by_name = True


class TaskResponse(TaskBase):
    """Full task response including computed fields"""
    task_id: int = Field(..., alias="taskId")
    status: str
    blocked_reason: Optional[str] = Field(None, alias="blockedReason")
    source: Optional[str] = None
    sprint_number: Optional[int] = Field(None, alias="sprintNumber")
    created_at: datetime = Field(..., alias="createdAt")
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    
    # Linked data
    projects: List[str] = Field(default_factory=list, description="Project codes")
    categories: List[str] = Field(default_factory=list, description="Category codes")
    primary_project: Optional[str] = Field(None, alias="primaryProject")
    
    # Computed
    days_overdue: Optional[int] = Field(None, alias="daysOverdue")
    is_cross_project: bool = Field(default=False, alias="isCrossProject")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class TaskListResponse(BaseModel):
    """Paginated list of tasks"""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    
    class Config:
        populate_by_name = True


class QuickCaptureRequest(BaseModel):
    """Minimal request for quick/voice capture"""
    title: str = Field(..., min_length=1, max_length=500)
    project: Optional[str] = Field(None, description="Single project code")
    category: Optional[str] = Field(default="IDEA", description="Single category code")
    
    
class QuickCaptureResponse(BaseModel):
    """Response confirming quick capture"""
    task_id: int = Field(..., alias="taskId")
    title: str
    project: Optional[str] = None
    category: str
    message: str = "Task captured successfully"
    
    class Config:
        populate_by_name = True

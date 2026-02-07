"""
MetaPM MCP Schemas
Pydantic models for MCP handoffs and tasks.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class HandoffDirection(str, Enum):
    CC_TO_AI = "cc_to_ai"
    AI_TO_CC = "ai_to_cc"


class HandoffStatus(str, Enum):
    PENDING = "pending"
    READ = "read"
    PROCESSED = "processed"
    ARCHIVED = "archived"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class AssignedTo(str, Enum):
    CC = "cc"
    COREY = "corey"
    CLAUDE_AI = "claude_ai"


# Handoff Schemas
class HandoffCreate(BaseModel):
    project: str = Field(..., max_length=100)
    task: str = Field(..., max_length=200)
    direction: HandoffDirection
    content: str
    metadata: Optional[Dict[str, Any]] = None
    response_to: Optional[str] = None


class HandoffUpdate(BaseModel):
    status: Optional[HandoffStatus] = None


class HandoffResponse(BaseModel):
    id: str
    project: str
    task: str
    direction: HandoffDirection
    status: HandoffStatus
    content: Optional[str] = None  # Only included in full response
    metadata: Optional[Dict[str, Any]] = None
    response_to: Optional[str] = None
    public_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class HandoffListResponse(BaseModel):
    handoffs: List[HandoffResponse]
    total: int
    has_more: bool


# Task Schemas
class TaskCreate(BaseModel):
    project: str = Field(..., max_length=100)
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: Optional[AssignedTo] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    related_handoff_id: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    assigned_to: Optional[AssignedTo] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: str
    project: str
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    status: TaskStatus
    assigned_to: Optional[AssignedTo] = None
    related_handoff_id: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    has_more: bool


# Log Entry Schema
class LogEntryType(str, Enum):
    HANDOFF = "handoff"
    TASK = "task"


class LogEntry(BaseModel):
    timestamp: datetime
    type: LogEntryType
    project: str
    summary: str
    id: str


class LogResponse(BaseModel):
    entries: List[LogEntry]

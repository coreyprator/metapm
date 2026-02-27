"""
Pydantic schemas for Roadmap feature (projects, requirements, sprints).
"""

from datetime import datetime, date
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


# Enums

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    STABLE = "stable"
    MAINTENANCE = "maintenance"
    PAUSED = "paused"


class RequirementType(str, Enum):
    FEATURE = "feature"
    BUG = "bug"
    ENHANCEMENT = "enhancement"
    TASK = "task"


class RequirementPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class RequirementStatus(str, Enum):
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    UAT = "uat"
    NEEDS_FIXES = "needs_fixes"
    CONDITIONAL_PASS = "conditional_pass"
    DONE = "done"


class SprintStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETE = "complete"


# Project schemas

class ProjectBase(BaseModel):
    code: str = Field(..., max_length=10)
    name: str = Field(..., max_length=100)
    emoji: Optional[str] = None
    color: Optional[str] = None
    current_version: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    repo_url: Optional[str] = None
    deploy_url: Optional[str] = None
    category_id: Optional[str] = None


class ProjectCreate(ProjectBase):
    id: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    color: Optional[str] = None
    current_version: Optional[str] = None
    status: Optional[ProjectStatus] = None
    repo_url: Optional[str] = None
    deploy_url: Optional[str] = None
    category_id: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int


# Sprint schemas

class SprintBase(BaseModel):
    project_id: Optional[str] = None
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    status: SprintStatus = SprintStatus.PLANNED
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SprintCreate(SprintBase):
    id: str


class SprintUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SprintStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SprintResponse(SprintBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class SprintListResponse(BaseModel):
    sprints: List[SprintResponse]
    total: int


# Requirement schemas

class RequirementBase(BaseModel):
    project_id: str
    code: str = Field(..., max_length=20)
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    type: RequirementType = RequirementType.TASK
    priority: RequirementPriority = RequirementPriority.P2
    status: RequirementStatus = RequirementStatus.BACKLOG
    target_version: Optional[str] = None
    sprint_id: Optional[str] = None
    handoff_id: Optional[str] = None
    uat_id: Optional[str] = None


class RequirementCreate(RequirementBase):
    id: str


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[RequirementType] = None
    priority: Optional[RequirementPriority] = None
    status: Optional[RequirementStatus] = None
    target_version: Optional[str] = None
    sprint_id: Optional[str] = None
    handoff_id: Optional[str] = None
    uat_id: Optional[str] = None


class RequirementResponse(RequirementBase):
    id: str
    created_at: datetime
    updated_at: datetime
    # Joined fields
    project_code: Optional[str] = None
    project_name: Optional[str] = None
    project_emoji: Optional[str] = None

    class Config:
        from_attributes = True


class RequirementListResponse(BaseModel):
    requirements: List[RequirementResponse]
    total: int


# Roadmap aggregated view

class ProjectRoadmapItem(BaseModel):
    project_id: str
    project_code: str
    project_name: str
    project_emoji: str
    current_version: Optional[str]
    requirements: List[RequirementResponse]


class RoadmapResponse(BaseModel):
    projects: List[ProjectRoadmapItem]
    stats: dict


# Category schemas (MP-021)

class CategoryResponse(BaseModel):
    id: str
    name: str
    display_order: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    display_order: int = 0


# Roadmap Task schemas (MP-012)

class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class RoadmapTaskCreate(BaseModel):
    id: Optional[str] = None
    requirement_id: str
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.BACKLOG
    priority: RequirementPriority = RequirementPriority.P2
    assignee: Optional[str] = None


class RoadmapTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[RequirementPriority] = None
    assignee: Optional[str] = None


class RoadmapTaskResponse(BaseModel):
    id: str
    requirement_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignee: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Test Plan / Test Case schemas (MP-013)

class TestCaseStatus(str, Enum):
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL_PASS = "conditional_pass"


class TestCaseCreate(BaseModel):
    title: str = Field(..., max_length=500)
    expected_result: Optional[str] = None


class TestCaseUpdate(BaseModel):
    status: Optional[TestCaseStatus] = None
    executed_at: Optional[datetime] = None


class TestCaseResponse(BaseModel):
    id: str
    test_plan_id: str
    title: str
    expected_result: Optional[str] = None
    status: str = "pending"
    executed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TestPlanCreate(BaseModel):
    requirement_id: str
    name: str = Field(..., max_length=200)
    test_cases: List[TestCaseCreate] = []


class TestPlanResponse(BaseModel):
    id: str
    requirement_id: str
    name: str
    created_at: datetime
    test_cases: List[TestCaseResponse] = []

    class Config:
        from_attributes = True


# Dependency schemas (MP-014)

class DependencyCreate(BaseModel):
    requirement_id: str
    depends_on_id: str


class DependencyResponse(BaseModel):
    id: str
    requirement_id: str
    depends_on_id: str
    depends_on_code: Optional[str] = None
    depends_on_title: Optional[str] = None
    depends_on_project_code: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

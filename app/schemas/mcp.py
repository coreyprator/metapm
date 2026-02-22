"""
MetaPM MCP Schemas
Pydantic models for MCP handoffs and tasks.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator, ValidationError
from pydantic_core import PydanticCustomError
from enum import Enum


class HandoffDirection(str, Enum):
    CC_TO_AI = "cc_to_ai"
    AI_TO_CC = "ai_to_cc"


class HandoffStatus(str, Enum):
    PENDING = "pending"
    READ = "read"
    PROCESSED = "processed"
    ARCHIVED = "archived"
    PENDING_UAT = "pending_uat"
    NEEDS_FIXES = "needs_fixes"
    DONE = "done"


class UATStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    CONDITIONAL_PASS = "conditional_pass"


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


# UAT Schemas
class UATResultItem(BaseModel):
    """A single UAT test result item from the HTML checklist."""
    id: str
    title: str
    status: str
    note: Optional[str] = Field(None, max_length=2000)
    linked_requirements: Optional[List[str]] = None


class UATSubmit(BaseModel):
    """Submit UAT results for a handoff."""
    status: UATStatus
    total_tests: int = Field(..., ge=0)
    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    blocked: Optional[int] = Field(0, ge=0)
    notes_count: Optional[int] = Field(0, ge=0)
    results_text: Optional[str] = None
    results: Optional[List[UATResultItem]] = None
    checklist_path: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def validate_results(cls, data: Any) -> Any:
        """Ensure at least one results format is provided and auto-generate results_text from results array if needed."""
        if isinstance(data, dict):
            results_text = data.get('results_text')
            results = data.get('results')
            
            # Validate: at least one results format required
            if not results_text and not results:
                raise PydanticCustomError(
                    'missing_results',
                    "Either 'results_text' or 'results' array is required"
                )
            
            # Auto-generate results_text from results array if not provided
            if not results_text and results:
                lines = []
                for r in results:
                    status_label = r.get('status', '').upper()
                    r_id = r.get('id', '')
                    r_title = r.get('title', '')
                    lines.append(f"  {status_label}  {r_id}: {r_title}")
                    if r.get('note'):
                        lines.append(f"        Note: {r['note']}")
                data['results_text'] = "\n".join(lines)
        
        return data


class UATResult(BaseModel):
    """Single UAT result."""
    id: str
    handoff_id: str
    status: UATStatus
    total_tests: int
    passed: int
    failed: int
    notes_count: Optional[int] = None
    results_text: Optional[str] = None
    tested_by: Optional[str] = None
    tested_at: datetime
    checklist_path: Optional[str] = None


class UATHistoryResponse(BaseModel):
    """UAT history for a handoff."""
    handoff_id: str
    uat_attempts: List[UATResult]
    latest_status: Optional[UATStatus] = None


# Direct UAT Submit (from checklist HTML)
class UATDirectSubmit(BaseModel):
    """Submit UAT results directly from HTML checklist."""
    project: Optional[str] = Field(None, max_length=100, strip_whitespace=True)
    version: Optional[str] = Field(None, max_length=200, strip_whitespace=True)
    uat_title: Optional[str] = Field(None, max_length=300, strip_whitespace=True)
    uat_date: Optional[str] = Field(None, max_length=50, strip_whitespace=True)
    feature: Optional[str] = Field(None, max_length=200, strip_whitespace=True)
    status: Optional[UATStatus] = None
    total_tests: int = Field(..., ge=0)
    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    blocked: Optional[int] = Field(0, ge=0)
    skipped: Optional[int] = Field(0, ge=0)
    notes_count: Optional[int] = Field(0, ge=0)
    results_text: Optional[str] = None
    results: Optional[List[UATResultItem]] = None
    notes: Optional[str] = None
    linked_requirements: Optional[List[str]] = None
    submitted_at: Optional[str] = None
    checklist_path: Optional[str] = None
    url: Optional[str] = None
    tested_by: Optional[str] = Field(None, max_length=100)

    @model_validator(mode='before')
    @classmethod
    def validate_and_prepare(cls, data: Any) -> Any:
        """Validate inputs and auto-generate results_text from results array if needed."""
        if isinstance(data, dict):
            # Normalize legacy fields
            if not data.get('submitted_at') and data.get('tested_at'):
                data['submitted_at'] = data.get('tested_at')
            if not data.get('notes') and data.get('general_notes'):
                data['notes'] = data.get('general_notes')

            if not data.get('version') and data.get('uat_date'):
                data['version'] = data.get('uat_date')

            if not data.get('uat_title') and data.get('title'):
                data['uat_title'] = data.get('title')

            results_text = data.get('results_text')
            results = data.get('results')

            # Normalize legacy results array fields (test_id/test_name/notes)
            if isinstance(results, list):
                normalized = []
                for item in results:
                    if not isinstance(item, dict):
                        normalized.append(item)
                        continue
                    if not item.get('id') and item.get('test_id'):
                        item['id'] = item.get('test_id')
                    if not item.get('title') and item.get('test_name'):
                        item['title'] = item.get('test_name')
                    if not item.get('status') and item.get('result'):
                        item['status'] = item.get('result')
                    if item.get('note') is None and item.get('notes'):
                        item['note'] = item.get('notes')
                    normalized.append(item)
                data['results'] = normalized
            
            # Validate: at least one results format required
            if not results_text and not results:
                raise PydanticCustomError(
                    'missing_results',
                    "Either 'results_text' or 'results' array is required"
                )
            
            # Validate: total_tests > 0
            total_tests = data.get('total_tests', 0)
            if total_tests <= 0:
                raise PydanticCustomError(
                    'invalid_total_tests',
                    "total_tests must be greater than 0"
                )
            
            # Validate: counts don't exceed total
            passed = data.get('passed', 0)
            failed = data.get('failed', 0)
            blocked = data.get('blocked', 0)
            if passed + failed + blocked > total_tests:
                raise PydanticCustomError(
                    'counts_exceed_total',
                    f"passed ({passed}) + failed ({failed}) + blocked ({blocked}) = "
                    f"{passed + failed + blocked} exceeds total_tests ({total_tests})"
                )

            # Default status if missing
            if not data.get('status'):
                data['status'] = 'failed' if failed and int(failed) > 0 else 'passed'

            # Default project if missing (derive from handoff_id prefix, if available)
            if not data.get('project'):
                handoff_id = data.get('handoff_id') or ''
                if handoff_id.startswith('HO-'):
                    token = handoff_id.split('-', 2)[1]
                    token_letters = ''.join([c for c in token if c.isalpha()]) or token
                else:
                    token = ''
                    token_letters = ''

                project_map = {
                    'EM03': 'Etymython',
                    'EM': 'Etymython',
                    'HL': 'HarmonyLab',
                    'AF': 'ArtForge',
                    'SF': 'Super-Flashcards',
                    'PM': 'project-methodology',
                    'MP': 'MetaPM',
                    'U9V1': 'MetaPM'
                }
                data['project'] = project_map.get(token, project_map.get(token_letters))
            
            # Auto-generate results_text from results array if not provided
            if not results_text and results:
                lines = []
                for r in results:
                    status_label = r.get('status', '').upper()
                    r_id = r.get('id', '')
                    r_title = r.get('title', '')
                    lines.append(f"  {status_label}  {r_id}: {r_title}")
                    if r.get('note'):
                        # Truncate long notes
                        note = r['note'][:2000] if len(r.get('note', '')) > 2000 else r['note']
                        lines.append(f"        Note: {note}")
                data['results_text'] = "\n".join(lines)
            
            # Append general notes if provided
            if data.get('notes') and data.get('results_text'):
                data['results_text'] = data['results_text'] + f"\n\nGeneral Notes:\n{data['notes']}"
        
        return data


class UATDirectSubmitResponse(BaseModel):
    """Response from direct UAT submit."""
    handoff_id: str
    uat_id: str
    status: str
    handoff_url: str
    message: str


class UATListItem(BaseModel):
    """UAT result with project info for list views."""
    id: str
    handoff_id: str
    project: Optional[str] = None
    version: Optional[str] = None
    status: UATStatus
    total_tests: int
    passed: int
    failed: int
    notes_count: Optional[int] = None
    tested_by: Optional[str] = None
    tested_at: datetime
    results_text: Optional[str] = None


class UATListResponse(BaseModel):
    """Paginated list of UAT results."""
    results: List[UATListItem]
    total: int

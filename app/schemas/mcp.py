"""
MetaPM MCP Schemas
Pydantic models for MCP handoffs and tasks.
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator, ValidationError
from pydantic_core import PydanticCustomError
from enum import Enum


# AP10: Shared validation helper for required non-N/A fields
_INVALID_VALUES = {'', 'n/a', 'na', 'null', 'none'}

def _is_invalid_field(value) -> bool:
    """Return True if value is null, empty, whitespace-only, or a placeholder like N/A."""
    if value is None:
        return True
    s = str(value).strip().lower()
    return s in _INVALID_VALUES


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
    # BA17 handoff_shells statuses
    SHELL_CREATED = "shell_created"
    CC_COMPLETE = "cc_complete"


class UATStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    CONDITIONAL_PASS = "conditional_pass"
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
    # BA04 format fields (optional — for new Bootstrap closeout flow)
    id: Optional[str] = Field(None, max_length=100)  # Custom ref ID e.g. "MP06-ABC"
    request_type: Optional[str] = Field(None, max_length=50)  # e.g. "Requirement"
    title: Optional[str] = Field(None, max_length=255)  # Sprint title
    description: Optional[str] = None  # Used as content when content not provided
    completion_handoff_url: Optional[str] = Field(None, max_length=500)  # GCS URL

    # AP10: pth and uat_url — required, validated at Pydantic level (un-bypassable)
    pth: Optional[str] = Field(None, max_length=20)  # Prompt tracking hash
    uat_url: Optional[str] = Field(None, max_length=500)  # UAT spec URL

    # PF5-MS2: Prompt linking (pth aliases to this if set)
    prompt_pth: Optional[str] = Field(None, max_length=20)

    # MP-HANDOFF-GATE-001: Enforcement fields
    uat_spec_id: Optional[str] = None  # Must reference a valid spec with BV items
    enforcement_bypass: Optional[str] = None  # "data_only_sprint" skips Gate 1 only

    # PA02-REQ-004: Version field (e.g. "3.6.2 → 3.6.3")
    version: Optional[str] = Field(None, max_length=50)

    # Existing fields (made optional for BA04 compat)
    project: str = Field(..., max_length=100)
    task: Optional[str] = Field(None, max_length=200)
    direction: Optional[HandoffDirection] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    response_to: Optional[str] = None
    completion_content: Optional[str] = None  # MM15-REQ-002: full CC deliverable report

    @model_validator(mode='after')
    def validate_and_normalize(self) -> 'HandoffCreate':
        # ── AP10 Gate: pth, uat_url, description required, non-N/A (un-bypassable) ──
        invalid_fields = []
        if _is_invalid_field(self.pth):
            invalid_fields.append('pth')
        if _is_invalid_field(self.uat_url):
            invalid_fields.append('uat_url')
        if _is_invalid_field(self.description):
            invalid_fields.append('description')
        if invalid_fields:
            msg = ", ".join(invalid_fields) + " required and cannot be N/A or empty"
            raise HTTPException(status_code=422, detail={"error": msg})

        # ── Normalize: pth → prompt_pth ──
        if self.pth and not self.prompt_pth:
            self.prompt_pth = self.pth

        # ── Normalize: extract uat_spec_id from uat_url if not explicitly set ──
        if self.uat_url and not self.uat_spec_id:
            # uat_url format: https://metapm.rentyourcio.com/uat/{uuid}
            match = re.search(r'/uat/([0-9a-fA-F-]{36})$', self.uat_url)
            if match:
                self.uat_spec_id = match.group(1)

        # ── BA04 normalization ──
        # task falls back to title, then id
        if not self.task:
            self.task = self.title or self.id or 'handoff'
        # direction defaults to cc_to_ai
        if not self.direction:
            self.direction = HandoffDirection.CC_TO_AI
        # content falls back to description
        if not self.content:
            self.content = self.description or ''
        return self


class HandoffUpdate(BaseModel):
    status: Optional[HandoffStatus] = None
    notified_at: Optional[str] = None  # PA02-REQ-001: ISO datetime string
    # BA17: shell field updates (used when patching a handoff_shell record)
    version_from: Optional[str] = None
    version_to: Optional[str] = None
    commit_hash: Optional[str] = None
    deploy_url: Optional[str] = None
    machine_tests: Optional[str] = None  # JSON array string
    deviations: Optional[str] = None
    notes: Optional[str] = None


class HandoffShellCreate(BaseModel):
    pth: str
    sprint_id: str
    project_code: str
    uat_spec_id: Optional[str] = None  # CAI pre-fills if UAT spec was already created


class HandoffShellResponse(BaseModel):
    handoff_id: str
    pth: str
    sprint_id: str
    project_code: str
    version_from: Optional[str] = None
    version_to: Optional[str] = None
    commit_hash: Optional[str] = None
    deploy_url: Optional[str] = None
    uat_spec_id: Optional[str] = None
    machine_tests: Optional[str] = None
    deviations: Optional[str] = None
    notes: Optional[str] = None
    patch_url: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


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
    review_id: Optional[str] = None
    assessment: Optional[str] = None
    pth: Optional[str] = None         # AP08 Fix 1: for Loop 2 email
    description: Optional[str] = None  # G2B18: stored on handoff record
    uat_url: Optional[str] = None      # G2B18: stored on handoff record
    uat_spec_id: Optional[str] = None  # AP08 Fix 1: for Loop 2 email UAT URL
    notified_at: Optional[datetime] = None  # PA02-REQ-001: email idempotency
    version: Optional[str] = None           # PA02-REQ-004: version shipped
    completion_handoff_url: Optional[str] = None  # PA02-REQ-003: GCS deliverable URL
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
class TestCaseInput(BaseModel):
    """Structured test case submitted by CC for server-side UAT generation."""
    id: str = Field(..., max_length=20)
    title: str = Field(..., max_length=300)
    type: str = Field("pl_visual", pattern=r"^(pl_visual|cc_machine)$")
    instructions: List[str] = Field(default_factory=list)
    expected: Optional[str] = Field(None, max_length=500)
    status: str = Field("pending", pattern=r"^(pending|pass|fail|skip)$")
    result: Optional[str] = None
    notes: Optional[str] = None


class UATResultItem(BaseModel):
    """A single UAT test result item from the HTML checklist."""
    id: str
    title: str
    status: str
    note: Optional[str] = Field(None, max_length=10000)
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
    total_tests: int = Field(0, ge=0)
    passed: int = Field(0, ge=0)
    failed: int = Field(0, ge=0)
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
    pth: Optional[str] = Field(None, max_length=20, description="Prompt Tracking Hash")
    cc_summary: Optional[str] = Field(None, max_length=5000, description="CC summary block (version, canaries, items to delete)")
    test_cases: Optional[List[TestCaseInput]] = Field(None, description="Structured test cases for server-side UAT generation")
    uat_checkpoint: Optional[str] = Field(None, max_length=100)
    uat_verification_hash: Optional[str] = Field(None, max_length=128)
    requirements: Optional[List[dict]] = Field(None, description="Requirements with evidence for verification")

    @model_validator(mode='before')
    @classmethod
    def validate_and_prepare(cls, data: Any) -> Any:
        """Validate inputs and auto-generate results_text from results array if needed."""
        if isinstance(data, dict):
            # Map legacy/alias field names for backward compatibility
            if not data.get('project') and data.get('project_name'):
                data['project'] = data['project_name']
            if not data.get('results_text'):
                if data.get('test_results_detail'):
                    data['results_text'] = data['test_results_detail']
                elif data.get('test_results_summary'):
                    data['results_text'] = data['test_results_summary']

            # Normalize linked_requirements: accept comma-separated string or list
            lr = data.get('linked_requirements')
            if isinstance(lr, str) and lr.strip():
                data['linked_requirements'] = [r.strip() for r in re.split(r'[,;]+', lr) if r.strip()]

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

            # Auto-generate results_text from results array if not provided
            if not results_text and results:
                lines = []
                for r in results:
                    status_label = r.get('status', '').upper()
                    r_id = r.get('id', '')
                    r_title = r.get('title', '')
                    lines.append(f"  {status_label}  {r_id}: {r_title}")
                    if r.get('note'):
                        note = r['note'][:10000] if len(r.get('note', '')) > 10000 else r['note']
                        lines.append(f"        Note: {note}")
                data['results_text'] = "\n".join(lines)

            # Infer total_tests from results_text if missing or zero
            total_tests = data.get('total_tests', 0)
            if not total_tests or int(total_tests) <= 0:
                rt = data.get('results_text', '') or ''
                # Count [XX-NN] test ID patterns
                test_ids = re.findall(r'\[[\w]+-\d+\]', rt)
                inferred_count = len(test_ids)
                if not inferred_count:
                    # Fallback: count lines containing status keywords
                    inferred_count = sum(
                        1 for line in rt.splitlines()
                        if any(kw in line.upper() for kw in ('PASS', 'FAIL', 'SKIP', 'PENDING'))
                    )
                data['total_tests'] = max(inferred_count, 1)

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

            # Append general notes if provided
            if data.get('notes') and data.get('results_text'):
                data['results_text'] = data['results_text'] + f"\n\nGeneral Notes:\n{data['notes']}"

            # MP-VERIFY-001: Validate requirements evidence
            reqs = data.get('requirements')
            if isinstance(reqs, list):
                for req in reqs:
                    if not isinstance(req, dict):
                        continue
                    if req.get('status') == 'complete' and not req.get('evidence'):
                        raise PydanticCustomError(
                            'missing_evidence',
                            f"Requirement '{req.get('code', '?')}' is marked 'complete' but has no 'evidence' object. "
                            "Complete requirements must include evidence (curl_command, http_status, response_preview)."
                        )

        return data


class UATDirectSubmitResponse(BaseModel):
    """Response from direct UAT submit."""
    handoff_id: str
    uat_id: str
    status: str
    handoff_url: str
    message: str
    checkpoint_verified: Optional[bool] = None


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
    pth: Optional[str] = None


class UATListResponse(BaseModel):
    """Paginated list of UAT results."""
    results: List[UATListItem]
    total: int


class TestCaseResultUpdate(BaseModel):
    """Single test case result from PL."""
    id: str
    status: str = Field(..., pattern=r"^(pass|fail|skip|pending)$")
    result: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=5000)


class UATResultsUpdate(BaseModel):
    """PATCH body for updating UAT test case results."""
    test_cases: List[TestCaseResultUpdate]
    overall_status: Optional[str] = Field(None, pattern=r"^(passed|failed|pending)$")


class BulkArchiveRequest(BaseModel):
    """Request to archive multiple UAT records."""
    uat_ids: List[str]
    reason: Optional[str] = Field("administrative cleanup", max_length=500)


class BulkCloseRequest(BaseModel):
    """AP09: Request to bulk-close UAT specs by spec_id."""
    spec_ids: List[str]
    reason: Optional[str] = Field("bulk-close", max_length=200)

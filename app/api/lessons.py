"""
Lessons Learned Fast-Routing (MP-LL-001).
POST   /api/lessons           — create draft lesson (auto LL-NNN)
GET    /api/lessons            — filterable list
GET    /api/lessons/pending    — approved but unapplied, by project
GET    /api/lessons/stats      — aggregate counts
GET    /api/lessons/{id}       — single lesson
PATCH  /api/lessons/{id}       — update status / text
POST   /api/lessons/apply      — legacy: commit lesson to GitHub (preserved)
"""

import logging
import base64
import hashlib
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query
import httpx

from app.core.config import settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Pydantic models ───────────────────────────────────────────────────

class LessonCreate(BaseModel):
    project: str
    category: str           # process | technical | architecture | quality
    lesson: str             # one sentence, actionable
    source_sprint: Optional[str] = None
    target: str             # bootstrap | pk.md | cai_memory | standards
    target_file: Optional[str] = None
    status: str = "draft"
    proposed_by: str = "cc"
    applied_in_sprint: Optional[str] = None


class LessonUpdate(BaseModel):
    status: Optional[str] = None
    applied_in_sprint: Optional[str] = None
    lesson: Optional[str] = None
    target_file: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────

def _next_ll_id() -> str:
    """Generate next LL-NNN id using transaction-safe MAX pattern."""
    result = execute_query("""
        SELECT MAX(TRY_CAST(SUBSTRING(id, 4, LEN(id)) AS INT)) AS max_num
        FROM lessons_learned
        WHERE id LIKE 'LL-%'
    """, fetch="one")
    next_num = (result['max_num'] or 0) + 1 if result else 1
    return f"LL-{next_num:03d}"


def _row_to_dict(row: dict) -> dict:
    """Convert DB row to API response dict."""
    return {
        "id": row["id"],
        "project": row["project"],
        "category": row["category"],
        "lesson": row["lesson"],
        "source_sprint": row.get("source_sprint"),
        "target": row["target"],
        "target_file": row.get("target_file"),
        "status": row["status"],
        "proposed_by": row.get("proposed_by", "cc"),
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
        "approved_at": str(row["approved_at"]) if row.get("approved_at") else None,
        "applied_at": str(row["applied_at"]) if row.get("applied_at") else None,
        "applied_in_sprint": row.get("applied_in_sprint"),
        "rag_ingested": bool(row.get("rag_ingested", 0)),
        "rag_ingested_at": str(row["rag_ingested_at"]) if row.get("rag_ingested_at") else None,
    }


async def _rag_ingest_lesson(lesson_dict: dict):
    """Best-effort ingest a lesson into Portfolio RAG lessons collection."""
    rag_url = settings.PORTFOLIO_RAG_URL
    if not rag_url:
        return False
    try:
        payload = {
            "collection": "lessons",
            "documents": [lesson_dict["lesson"]],
            "ids": [lesson_dict["id"]],
            "metadatas": [{
                "project": lesson_dict["project"],
                "category": lesson_dict["category"],
                "target": lesson_dict["target"],
                "source_sprint": lesson_dict.get("source_sprint") or "",
                "status": lesson_dict["status"],
                "proposed_by": lesson_dict.get("proposed_by", "cc"),
            }]
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{rag_url}/ingest/custom", json=payload)
            if resp.status_code in (200, 201):
                execute_query("""
                    UPDATE lessons_learned
                    SET rag_ingested = 1, rag_ingested_at = GETDATE()
                    WHERE id = ?
                """, (lesson_dict["id"],), fetch="none")
                return True
            else:
                logger.warning(f"RAG ingest failed for {lesson_dict['id']}: {resp.status_code}")
    except Exception as e:
        logger.warning(f"RAG ingest error for {lesson_dict['id']}: {e}")
    return False


# ── POST /api/lessons ─────────────────────────────────────────────────

@router.post("/lessons")
async def create_lesson(body: LessonCreate):
    """Create a draft lesson with auto-generated LL-NNN id."""
    # Validate enums
    if body.category not in ("process", "technical", "architecture", "quality"):
        raise HTTPException(400, f"Invalid category: {body.category}")
    if body.target not in ("bootstrap", "pk.md", "cai_memory", "standards"):
        raise HTTPException(400, f"Invalid target: {body.target}")
    if body.proposed_by not in ("cc", "cai", "pl"):
        raise HTTPException(400, f"Invalid proposed_by: {body.proposed_by}")
    if body.status not in ("draft", "approved", "applied", "rejected"):
        raise HTTPException(400, f"Invalid status: {body.status}")

    ll_id = _next_ll_id()

    # Set timestamps based on status
    approved_at = "GETDATE()" if body.status in ("approved", "applied") else "NULL"
    applied_at = "GETDATE()" if body.status == "applied" else "NULL"

    execute_query(f"""
        INSERT INTO lessons_learned
            (id, project, category, lesson, source_sprint, target, target_file,
             status, proposed_by, created_at, approved_at, applied_at, applied_in_sprint)
        VALUES
            (?, ?, ?, ?, ?, ?, ?,
             ?, ?, GETDATE(), {approved_at}, {applied_at}, ?)
    """, (
        ll_id, body.project, body.category, body.lesson,
        body.source_sprint, body.target, body.target_file,
        body.status, body.proposed_by, body.applied_in_sprint
    ), fetch="none")

    row = execute_query("SELECT * FROM lessons_learned WHERE id = ?", (ll_id,), fetch="one")
    lesson_dict = _row_to_dict(row)

    # Best-effort RAG ingest
    await _rag_ingest_lesson(lesson_dict)

    # Checkpoint
    ck = hashlib.sha256(f"{ll_id}:{body.status}".encode()).hexdigest()[:4].upper()
    lesson_dict["checkpoint"] = ck
    return lesson_dict


# ── GET /api/lessons ──────────────────────────────────────────────────

@router.get("/lessons")
async def list_lessons(
    project: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    target: Optional[str] = None,
    proposed_by: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """Filterable list of lessons, ordered by created_at DESC."""
    conditions = []
    params = []
    if project:
        conditions.append("project = ?")
        params.append(project)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if target:
        conditions.append("target = ?")
        params.append(target)
    if proposed_by:
        conditions.append("proposed_by = ?")
        params.append(proposed_by)

    where = " AND ".join(conditions) if conditions else "1=1"
    params.extend([offset, limit])

    rows = execute_query(f"""
        SELECT * FROM lessons_learned
        WHERE {where}
        ORDER BY created_at DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """, tuple(params), fetch="all") or []

    count_row = execute_query(f"""
        SELECT COUNT(*) as total FROM lessons_learned WHERE {where}
    """, tuple(params[:-2]) if conditions else None, fetch="one")
    total = count_row["total"] if count_row else len(rows)

    return {"lessons": [_row_to_dict(r) for r in rows], "total": total}


# ── GET /api/lessons/pending — MUST be before /{id} ───────────────────

@router.get("/lessons/pending")
async def pending_lessons(project: Optional[str] = None):
    """Lessons approved but not yet applied. Called by CC in Phase 0."""
    params = []
    where = "status = 'approved' AND applied_at IS NULL"
    if project:
        where += " AND project = ?"
        params.append(project)

    rows = execute_query(f"""
        SELECT * FROM lessons_learned
        WHERE {where}
        ORDER BY created_at ASC
    """, tuple(params) if params else None, fetch="all") or []

    return {"lessons": [_row_to_dict(r) for r in rows], "count": len(rows)}


# ── GET /api/lessons/stats ────────────────────────────────────────────

@router.get("/lessons/stats")
async def lesson_stats():
    """Aggregate counts by status, project, category."""
    total_row = execute_query("SELECT COUNT(*) as total FROM lessons_learned", fetch="one")
    total = total_row["total"] if total_row else 0

    status_rows = execute_query("""
        SELECT status, COUNT(*) as cnt FROM lessons_learned GROUP BY status
    """, fetch="all") or []
    by_status = {r["status"]: r["cnt"] for r in status_rows}

    project_rows = execute_query("""
        SELECT project, COUNT(*) as cnt FROM lessons_learned GROUP BY project
    """, fetch="all") or []
    by_project = {r["project"]: r["cnt"] for r in project_rows}

    category_rows = execute_query("""
        SELECT category, COUNT(*) as cnt FROM lessons_learned GROUP BY category
    """, fetch="all") or []
    by_category = {r["category"]: r["cnt"] for r in category_rows}

    return {
        "total": total,
        "by_status": by_status,
        "by_project": by_project,
        "by_category": by_category,
        "pending_approval": by_status.get("draft", 0),
        "pending_application": by_status.get("approved", 0),
    }


# ── GET /api/lessons/recent (legacy) ─────────────────────────────────

@router.get("/lessons/recent")
async def recent_lessons():
    """Return the last 20 lessons (legacy endpoint, reads from lessons_learned)."""
    rows = execute_query("""
        SELECT TOP 20 * FROM lessons_learned ORDER BY created_at DESC
    """, fetch="all") or []
    return {"lessons": [_row_to_dict(r) for r in rows]}


# ── GET /api/lessons/{id} ─────────────────────────────────────────────

@router.get("/lessons/{lesson_id}")
async def get_lesson(lesson_id: str):
    """Get a single lesson by ID."""
    row = execute_query("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,), fetch="one")
    if not row:
        raise HTTPException(404, f"Lesson {lesson_id} not found")
    return _row_to_dict(row)


# ── PATCH /api/lessons/{id} ───────────────────────────────────────────

@router.patch("/lessons/{lesson_id}")
async def update_lesson(lesson_id: str, body: LessonUpdate):
    """Update lesson status/text. Auto-sets timestamps."""
    row = execute_query("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,), fetch="one")
    if not row:
        raise HTTPException(404, f"Lesson {lesson_id} not found")

    updates = []
    params = []

    if body.status:
        if body.status not in ("draft", "approved", "applied", "rejected"):
            raise HTTPException(400, f"Invalid status: {body.status}")
        updates.append("status = ?")
        params.append(body.status)
        if body.status == "approved":
            updates.append("approved_at = GETDATE()")
        elif body.status == "applied":
            updates.append("applied_at = GETDATE()")
            if not body.applied_in_sprint:
                raise HTTPException(400, "applied_in_sprint required when status=applied")
            updates.append("applied_in_sprint = ?")
            params.append(body.applied_in_sprint)

    if body.lesson:
        updates.append("lesson = ?")
        params.append(body.lesson)

    if body.target_file:
        updates.append("target_file = ?")
        params.append(body.target_file)

    if body.applied_in_sprint and body.status != "applied":
        updates.append("applied_in_sprint = ?")
        params.append(body.applied_in_sprint)

    if not updates:
        raise HTTPException(400, "No fields to update")

    params.append(lesson_id)
    execute_query(f"""
        UPDATE lessons_learned SET {', '.join(updates)} WHERE id = ?
    """, tuple(params), fetch="none")

    updated = execute_query("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,), fetch="one")
    lesson_dict = _row_to_dict(updated)

    # Re-ingest to RAG if already ingested and status changed
    if row.get("rag_ingested") and body.status:
        await _rag_ingest_lesson(lesson_dict)

    return lesson_dict


# ── POST /api/lessons/apply (legacy: commit to GitHub) ────────────────

GITHUB_API = "https://api.github.com"
GITHUB_OWNER = "coreyprator"
GCP_PROJECT = "super-flashcards-475210"
SECRET_NAME = "portfolio-rag-github-token"

KNOWN_REPOS = {
    "harmonylab", "super-flashcards", "metapm", "portfolio-rag",
    "project-methodology", "audioflair",
}


def _get_github_token() -> str:
    """Get GitHub PAT from Secret Manager."""
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT}/secrets/{SECRET_NAME}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        logger.error(f"Failed to get GitHub token from Secret Manager: {e}")
        raise HTTPException(status_code=500, detail=f"GitHub token unavailable: {e}")


@router.post("/lessons/apply")
async def apply_lesson(body: dict):
    """Legacy: Apply a lesson by committing directly to GitHub."""
    required = ['target_repo', 'target_file', 'target_section', 'lesson_text', 'source_sprint', 'category', 'applied_by']
    for field in required:
        if not body.get(field):
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    target_repo = body['target_repo']
    target_file = body['target_file']
    target_section = body['target_section']
    lesson_text = body['lesson_text']
    source_sprint = body['source_sprint']
    category = body['category']

    if target_repo not in KNOWN_REPOS:
        raise HTTPException(status_code=400, detail=f"Unknown repo '{target_repo}'. Known: {sorted(KNOWN_REPOS)}")

    valid_categories = ['BOOTSTRAP', 'PROJECT', 'CAI_PROCESS', 'METHODOLOGY', 'PORTFOLIO_RAG']
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category '{category}'. Valid: {valid_categories}")

    token = _get_github_token()
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{GITHUB_API}/repos/{GITHUB_OWNER}/{target_repo}/contents/{target_file}"
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"File not found: {target_repo}/{target_file}")
            resp.raise_for_status()

            file_data = resp.json()
            file_sha = file_data['sha']
            content = base64.b64decode(file_data['content']).decode('utf-8')

            if target_section not in content:
                headers_found = [line.strip() for line in content.split('\n') if line.strip().startswith('##')]
                raise HTTPException(400, f"Section '{target_section}' not found. Available: {headers_found}")

            check_text = lesson_text.strip()[:60]
            if check_text in content:
                return {"already_applied": True, "target_repo": target_repo, "target_file": target_file, "note": "Lesson text already exists."}

            section_idx = content.index(target_section)
            newline_idx = content.index('\n', section_idx)
            new_content = content[:newline_idx + 1] + lesson_text + '\n' + content[newline_idx + 1:]

            short_desc = lesson_text.split('\n')[0][:60].strip('- ')
            commit_msg = f"docs: LL from {source_sprint} - {short_desc}"

            new_content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
            put_resp = await client.put(url, headers=headers, json={
                "message": commit_msg,
                "content": new_content_b64,
                "sha": file_sha,
            })
            if put_resp.status_code not in (200, 201):
                raise HTTPException(502, f"GitHub commit failed: {put_resp.status_code}")

            commit_sha = put_resp.json().get('commit', {}).get('sha', 'unknown')

            return {
                "applied": True, "commit_sha": commit_sha[:7],
                "target_repo": target_repo, "target_file": target_file,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lesson apply error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

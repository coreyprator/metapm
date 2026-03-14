"""
Bulk Seed API — MP-SEED-FORM-001 (PTH-UG06)
Endpoints for bulk-creating requirements and lessons from JSON arrays.
Idempotent: skips records whose code already exists (unless force=true).
"""
import json
import logging
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query

from app.core.database import execute_query

logger = logging.getLogger(__name__)
router = APIRouter()


# ---- Pydantic Models ----

class SeedRequirement(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    project_id: str = Field(..., min_length=1)
    status: str = Field(default="build")
    priority: str = Field(default="P2")
    type: str = Field(default="feature")
    pth: Optional[str] = None
    notes: Optional[str] = None
    estimate_hours: Optional[float] = None


class SeedLesson(BaseModel):
    title: str = Field(..., min_length=1)
    lesson: str = Field(..., min_length=1)
    project: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    severity: Optional[str] = Field(default="medium")
    pth: Optional[str] = None
    target: str = Field(default="bootstrap")
    source_sprint: Optional[str] = None
    proposed_by: str = Field(default="pl")


# ---- Endpoints ----

@router.post("/api/seed/requirements")
async def seed_requirements(
    items: List[SeedRequirement],
    force: bool = Query(False, description="If true, update existing records instead of skipping")
):
    """Bulk create requirements. Skips records whose code already exists unless force=true."""
    created = 0
    skipped = 0
    updated = 0
    errors = []

    for item in items:
        try:
            # Check if code already exists
            existing = execute_query(
                "SELECT id FROM roadmap_requirements WHERE code = ?",
                (item.code,), fetch="one"
            )

            if existing and not force:
                skipped += 1
                continue

            if existing and force:
                # Update existing record
                execute_query("""
                    UPDATE roadmap_requirements
                    SET title = ?, description = ?, project_id = ?,
                        status = ?, priority = ?, type = ?,
                        pth = ?, updated_at = GETUTCDATE()
                    WHERE code = ?
                """, (
                    item.title, item.description, item.project_id,
                    item.status, item.priority, item.type,
                    item.pth, item.code
                ), fetch="none")
                updated += 1
                continue

            # Create new
            req_id = str(uuid.uuid4())
            execute_query("""
                INSERT INTO roadmap_requirements
                    (id, project_id, code, title, description, type, priority, status, pth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req_id, item.project_id, item.code, item.title,
                item.description, item.type, item.priority, item.status,
                item.pth
            ), fetch="none")
            created += 1

        except Exception as e:
            errors.append({"code": item.code, "reason": str(e)})
            logger.warning(f"Seed requirement {item.code} failed: {e}")

    logger.info(f"Seed requirements: created={created} skipped={skipped} updated={updated} errors={len(errors)}")
    return {
        "created": created,
        "skipped": skipped,
        "updated": updated,
        "errors": errors
    }


@router.post("/api/seed/lessons")
async def seed_lessons(
    items: List[SeedLesson],
    force: bool = Query(False)
):
    """Bulk create lessons learned. Uses title+project for duplicate detection."""
    created = 0
    skipped = 0
    errors = []

    # Get next LL-id
    def next_ll_id():
        row = execute_query(
            "SELECT TOP 1 id FROM lessons_learned ORDER BY created_at DESC",
            fetch="one"
        )
        if row and row["id"].startswith("LL-"):
            try:
                num = int(row["id"].split("-")[1])
                return f"LL-{num + 1:03d}"
            except (ValueError, IndexError):
                pass
        return "LL-001"

    for item in items:
        try:
            # Check for duplicate by title + project
            existing = execute_query(
                "SELECT id FROM lessons_learned WHERE lesson LIKE ? AND project = ?",
                (f"%{item.title}%", item.project), fetch="one"
            )

            if existing and not force:
                skipped += 1
                continue

            ll_id = next_ll_id()
            lesson_text = f"{item.title}: {item.lesson}" if item.title not in item.lesson else item.lesson

            execute_query("""
                INSERT INTO lessons_learned
                    (id, project, category, lesson, source_sprint, target,
                     status, proposed_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, GETDATE())
            """, (
                ll_id, item.project, item.category, lesson_text,
                item.source_sprint, item.target, item.proposed_by
            ), fetch="none")
            created += 1

        except Exception as e:
            errors.append({"title": item.title, "reason": str(e)})
            logger.warning(f"Seed lesson '{item.title}' failed: {e}")

    logger.info(f"Seed lessons: created={created} skipped={skipped} errors={len(errors)}")
    return {
        "created": created,
        "skipped": skipped,
        "errors": errors
    }

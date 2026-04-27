"""
Bug Classifier Inspector API — MP56
Endpoints for the PL bug classification & chain management surface.
REQ-117 / sprint MP56-BUG-INSPECTOR-001
"""

import json
import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ClassificationUpdate(BaseModel):
    classifications: Optional[List[str]] = None
    bug_chain_ids: Optional[List[str]] = None


class ClassificationCreate(BaseModel):
    name: str
    description: str
    display_order: Optional[int] = None
    active: bool = True
    code: Optional[str] = None


class BugChainCreate(BaseModel):
    id: str
    pattern_label: str
    expected_outcome: str
    missing_signal: str
    tokens: Optional[List[str]] = None
    status: Optional[str] = "open"
    failure_class_hash: Optional[str] = None


class BugChainMemberAdd(BaseModel):
    code: str


class BugChainMerge(BaseModel):
    target: str


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

async def load_classifications() -> List[Dict[str, Any]]:
    """Load all classifications from the classifications table."""
    rows = execute_query(
        """
        SELECT code, name, description, display_order, active
        FROM classifications
        ORDER BY display_order, name
        """
    ) or []
    return [dict(r) for r in rows]


async def load_chains() -> List[Dict[str, Any]]:
    """Load all bug chains with their members. Returns empty if table doesn't exist yet."""
    try:
        chains = execute_query(
            """
            SELECT
                id,
                pattern_label,
                expected_outcome,
                tokens,
                member_requirement_codes,
                total_occurrences,
                status,
                failure_class_hash,
                first_occurrence_requirement_code,
                first_occurrence_at
            FROM bug_chains
            ORDER BY total_occurrences DESC
            """
        ) or []
    except Exception as e:
        logger.warning(f"bug_chains query failed (table may not exist yet): {e}")
        return []

    result = []
    for c in chains:
        # Parse JSON fields
        tokens = []
        if c.get("tokens"):
            try:
                tokens = json.loads(c["tokens"]) if isinstance(c["tokens"], str) else c["tokens"]
            except:
                tokens = []

        member_codes = []
        if c.get("member_requirement_codes"):
            try:
                member_codes = json.loads(c["member_requirement_codes"]) if isinstance(c["member_requirement_codes"], str) else c["member_requirement_codes"]
            except:
                member_codes = []

        result.append({
            "id": c["id"],
            "pattern_label": c["pattern_label"],
            "expected_outcome": c.get("expected_outcome") or "",
            "missing_signal": c.get("missing_signal") or "",
            "tokens": tokens,
            "member_requirement_codes": member_codes,
            "total_occurrences": c.get("total_occurrences") or 0,
            "status": c.get("status") or "open",
            "failure_class_hash": c.get("failure_class_hash"),
            "first_occurrence_requirement_code": c.get("first_occurrence_requirement_code"),
            "first_occurrence_at": str(c["first_occurrence_at"]) if c.get("first_occurrence_at") else None,
        })

    return result


async def load_bugs_with_context() -> List[Dict[str, Any]]:
    """
    Load all bugs (type='bug') with full context including:
    - Bug-level classifications from bug_classifications join table
    - Chain membership from bug_chain_members
    - UAT walks with BVs
    - Sprint history
    - Handoffs
    - Reviews
    - Status history
    """
    # Get all bugs (MP56-PATCH: sprint_id removed - not in roadmap_requirements table)
    bugs = execute_query(
        """
        SELECT
            id, code, title, description, status, priority, type,
            pth, failure_class_hash, created_at, updated_at,
            project_id
        FROM roadmap_requirements
        WHERE type = 'bug'
        ORDER BY created_at DESC
        """
    ) or []

    result = []
    for bug in bugs:
        bug_code = bug["code"]
        bug_req_id = bug["id"]

        # Get classifications for this bug from bug_classifications join table
        bug_cls = execute_query(
            """
            SELECT classification_code
            FROM bug_classifications
            WHERE bug_requirement_id = ?
            """,
            (bug_req_id,)
        ) or []
        classifications = [r["classification_code"] for r in bug_cls]

        # Get chain IDs from bug_chain_members
        bug_chains = execute_query(
            """
            SELECT chain_id
            FROM bug_chain_members
            WHERE bug_requirement_id = ?
            """,
            (bug_req_id,)
        ) or []
        bug_chain_ids = [r["chain_id"] for r in bug_chains]

        # Get UAT walks via pth_registry (MP56-PATCH: fixed uat_page_id error)
        uat_walks = []
        walks = execute_query(
            """
            SELECT
                u.id, u.pth, cp.sprint_id, u.status,
                u.pl_submitted_at, u.general_notes, u.version
            FROM pth_registry pr
            JOIN uat_pages u ON u.pth = pr.pth
            LEFT JOIN cc_prompts cp ON cp.pth = u.pth
            WHERE pr.requirement_id = ?
            ORDER BY u.pl_submitted_at DESC
            """,
            (bug_req_id,)
        ) or []

        for walk in walks:
            # Get BVs for this UAT walk (MP56-PATCH: removed bv_type - not in table)
            bvs = execute_query(
                """
                SELECT
                    bv_id, title, status, classification,
                    notes, cc_evidence, cc_result
                FROM uat_bv_items
                WHERE spec_id = ?
                ORDER BY bv_id
                """,
                (walk["id"],)
            ) or []

            # Per API.md: BV classification is singular in DB but we return as array for forward-compat
            for bv in bvs:
                bv["classifications"] = [bv["classification"]] if bv.get("classification") else []
                del bv["classification"]  # Remove singular field

            uat_walks.append({
                "id": walk["id"],
                "pth": walk["pth"],
                "sprint_id": walk["sprint_id"],
                "uat_status": walk["status"],  # Map status → uat_status for frontend
                "submitted_at": str(walk["pl_submitted_at"]) if walk.get("pl_submitted_at") else None,
                "general_notes": walk.get("general_notes"),
                "version": walk.get("version", ""),
                "bvs": [dict(bv) for bv in bvs],
            })

        # Get sprint history via cc_prompts (MP56-PATCH: use requirement_id not pth)
        sprints = []
        sprint_rows = execute_query(
            """
            SELECT
                id, sprint_id, pth, status, session_outcome,
                approved_at, approved_by, also_closes,
                session_started_at, session_ended_at, session_stop_reason,
                content
            FROM cc_prompts
            WHERE requirement_id = ?
            ORDER BY created_at DESC
            """,
            (bug_req_id,)
        ) or []

        for s in sprint_rows:
            also_closes = []
            if s.get("also_closes"):
                try:
                    also_closes = json.loads(s["also_closes"]) if isinstance(s["also_closes"], str) else s["also_closes"]
                except:
                    also_closes = []

            sprints.append({
                "id": s["id"],
                "sprint_id": s["sprint_id"],
                "pth": s["pth"],
                "status": s["status"],
                "session_outcome": s.get("session_outcome"),
                "approved_at": str(s["approved_at"]) if s.get("approved_at") else None,
                "approved_by": s.get("approved_by"),
                "also_closes": also_closes,
                "content": s.get("content", "")[:500],  # Truncate for response size
                "session_started_at": str(s["session_started_at"]) if s.get("session_started_at") else None,
                "session_ended_at": str(s["session_ended_at"]) if s.get("session_ended_at") else None,
                "session_stop_reason": s.get("session_stop_reason"),
            })

        # Get handoffs (MP56-PATCH: use pth_registry)
        handoffs = []
        handoff_rows = execute_query(
            """
            SELECT
                h.id, h.pth, h.direction, h.description, h.evidence_json
            FROM mcp_handoffs h
            WHERE h.pth IN (SELECT pth FROM pth_registry WHERE requirement_id = ?)
            ORDER BY h.created_at DESC
            """,
            (bug_req_id,)
        ) or []

        for h in handoff_rows:
            evidence = {}
            if h.get("evidence_json"):
                try:
                    evidence = json.loads(h["evidence_json"]) if isinstance(h["evidence_json"], str) else h["evidence_json"]
                except:
                    evidence = {}

            handoffs.append({
                "id": h["id"],
                "pth": h["pth"],
                "direction": h["direction"],
                "description": h.get("description", ""),
                "evidence_json": evidence,
            })

        # Get reviews (MP56-PATCH: column is prompt_pth not pth, no created_by)
        reviews = []
        if handoffs:
            for handoff in handoffs:
                review_rows = execute_query(
                    """
                    SELECT
                        id, prompt_pth, handoff_id, assessment, notes,
                        lesson_candidates, created_at
                    FROM reviews
                    WHERE handoff_id = ?
                    ORDER BY created_at DESC
                    """,
                    (handoff["id"],)
                ) or []

                for r in review_rows:
                    lesson_cand = {}
                    if r.get("lesson_candidates"):
                        try:
                            lesson_cand = json.loads(r["lesson_candidates"]) if isinstance(r["lesson_candidates"], str) else r["lesson_candidates"]
                        except:
                            lesson_cand = {}

                    reviews.append({
                        "id": r["id"],
                        "pth": r["prompt_pth"],  # Map prompt_pth → pth for frontend
                        "handoff_id": r["handoff_id"],
                        "assessment": r["assessment"],
                        "notes": r.get("notes", ""),
                        "lesson_candidates": lesson_cand,
                        "created_at": str(r["created_at"]) if r.get("created_at") else None,
                    })

        # Get status history from requirement_history (MP56-PATCH: use old_value/new_value not old_status/new_status)
        history = execute_query(
            """
            SELECT
                id, old_value AS old_status, new_value AS new_status, changed_at, changed_by, notes AS note
            FROM requirement_history
            WHERE requirement_id = ?
              AND field_name = 'status'
            ORDER BY changed_at ASC
            """,
            (bug_req_id,)
        ) or []

        history_items = []
        for h in history:
            history_items.append({
                "id": h["id"],
                "old_status": h.get("old_status"),
                "new_status": h["new_status"],
                "changed_at": str(h["changed_at"]) if h.get("changed_at") else None,
                "changed_by": h.get("changed_by"),
                "note": h.get("note", ""),
            })

        # Calculate age in days
        age_days = 0
        if bug.get("created_at"):
            from datetime import datetime
            try:
                created = bug["created_at"]
                if isinstance(created, str):
                    created = datetime.fromisoformat(created)
                age_days = (datetime.utcnow() - created.replace(tzinfo=None)).days
            except:
                age_days = 0

        # Build final bug object (MP56-PATCH: sprint_id removed - bugs have many sprints)
        result.append({
            "code": bug_code,
            "title": bug["title"],
            "description": bug.get("description", ""),
            "status": bug["status"],
            "priority": bug.get("priority", "P2"),
            "type": bug["type"],
            "layer": "unknown",  # TODO: Add layer field to schema or derive
            "prefix": bug_code.split("-")[0] if "-" in bug_code else bug_code[:3],
            "pth": bug.get("pth"),
            "failure_class_hash": bug.get("failure_class_hash"),
            "bug_chain_ids": bug_chain_ids,  # M:N array
            "classifications": classifications,  # M:N array
            "created_at": str(bug["created_at"]) if bug.get("created_at") else None,
            "updated_at": str(bug["updated_at"]) if bug.get("updated_at") else None,
            "age": age_days,
            "uat_walks": uat_walks,
            "sprints": sprints,
            "handoffs": handoffs,
            "reviews": reviews,
            "history": history_items,
        })

    return result


# ---------------------------------------------------------------------------
# B.1 — GET /api/classifier/bootstrap
# ---------------------------------------------------------------------------

@router.get("/api/classifier/bootstrap")
async def classifier_bootstrap():
    """
    Initial hydration endpoint for the Bug Classifier UI.
    Returns all bugs with full context, all classifications, and all chains.
    """
    try:
        bugs = await load_bugs_with_context()
        classifications = await load_classifications()
        chains = await load_chains()

        return {
            "bugs": bugs,
            "classifications": classifications,
            "chains": chains,
        }
    except Exception as exc:
        logger.error(f"classifier_bootstrap failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# C.1 — PATCH /api/bugs/:code
# ---------------------------------------------------------------------------

@router.patch("/api/bugs/{bug_code}")
async def update_bug(bug_code: str, update: ClassificationUpdate):
    """
    Update bug classifications and/or chain assignments.
    Replaces entire M:N relationships (not incremental).
    """
    try:
        # Get bug requirement_id
        bug_rows = execute_query(
            """
            SELECT id
            FROM roadmap_requirements
            WHERE code = ? AND type = 'bug'
            """,
            (bug_code,)
        )
        if not bug_rows:
            raise HTTPException(status_code=404, detail=f"Bug {bug_code} not found")

        bug_req_id = bug_rows[0]["id"]

        # Update classifications if provided
        if update.classifications is not None:
            # Delete existing
            execute_query(
                "DELETE FROM bug_classifications WHERE bug_requirement_id = ?",
                (bug_req_id,)
            )
            # Insert new
            for cls_code in update.classifications:
                execute_query(
                    """
                    INSERT INTO bug_classifications (bug_requirement_id, classification_code, created_by)
                    VALUES (?, ?, 'CC')
                    """,
                    (bug_req_id, cls_code)
                )
            logger.info(f"Updated classifications for {bug_code}: {update.classifications}")

        # Update chain memberships if provided
        if update.bug_chain_ids is not None:
            # Delete existing
            execute_query(
                "DELETE FROM bug_chain_members WHERE bug_requirement_id = ?",
                (bug_req_id,)
            )
            # Insert new
            for chain_id in update.bug_chain_ids:
                execute_query(
                    """
                    INSERT INTO bug_chain_members (bug_requirement_id, chain_id, created_by)
                    VALUES (?, ?, 'CC')
                    """,
                    (bug_req_id, chain_id)
                )
            logger.info(f"Updated chain memberships for {bug_code}: {update.bug_chain_ids}")

        return {"success": True, "code": bug_code}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"update_bug failed for {bug_code}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# C.2 — Classifications CRUD
# ---------------------------------------------------------------------------

@router.post("/api/classifications")
async def create_classification(cls: ClassificationCreate):
    """Create a new classification."""
    try:
        # Auto-generate code if not provided
        code = cls.code or cls.name.lower().replace(" ", "_")

        # Default display_order to max+1 if not provided
        display_order = cls.display_order
        if display_order is None:
            max_rows = execute_query("SELECT MAX(display_order) as max_order FROM classifications")
            max_order = max_rows[0]["max_order"] if max_rows and max_rows[0]["max_order"] else 0
            display_order = max_order + 1

        execute_query(
            """
            INSERT INTO classifications (code, name, description, display_order, active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, cls.name, cls.description, display_order, cls.active)
        )

        logger.info(f"Created classification: {code}")
        return {"success": True, "code": code}

    except Exception as exc:
        logger.error(f"create_classification failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/api/classifications/{cls_code}")
async def update_classification(cls_code: str, cls: ClassificationCreate):
    """Update an existing classification."""
    try:
        # Check if exists
        existing = execute_query(
            "SELECT code FROM classifications WHERE code = ?",
            (cls_code,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail=f"Classification {cls_code} not found")

        execute_query(
            """
            UPDATE classifications
            SET name = ?, description = ?, display_order = ?, active = ?
            WHERE code = ?
            """,
            (cls.name, cls.description, cls.display_order, cls.active, cls_code)
        )

        logger.info(f"Updated classification: {cls_code}")
        return {"success": True, "code": cls_code}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"update_classification failed for {cls_code}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/classifications/{cls_code}")
async def delete_classification(cls_code: str):
    """Delete a classification (soft delete via active=false)."""
    try:
        # Check if exists
        existing = execute_query(
            "SELECT code FROM classifications WHERE code = ?",
            (cls_code,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail=f"Classification {cls_code} not found")

        # Soft delete
        execute_query(
            "UPDATE classifications SET active = 0 WHERE code = ?",
            (cls_code,)
        )

        logger.info(f"Deleted (soft) classification: {cls_code}")
        return {"success": True, "code": cls_code}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"delete_classification failed for {cls_code}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# C.3 — Bug Chains CRUD
# ---------------------------------------------------------------------------

@router.post("/api/chains")
async def create_chain(chain: BugChainCreate):
    """Create a new bug chain."""
    try:
        # Convert tokens list to JSON string if provided
        tokens_json = json.dumps(chain.tokens) if chain.tokens else None

        execute_query(
            """
            INSERT INTO bug_chains (
                id, pattern_label, expected_outcome, missing_signal,
                tokens, status, failure_class_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chain.id,
                chain.pattern_label,
                chain.expected_outcome,
                chain.missing_signal,
                tokens_json,
                chain.status,
                chain.failure_class_hash
            )
        )

        logger.info(f"Created bug chain: {chain.id}")
        return {"success": True, "id": chain.id}

    except Exception as exc:
        logger.error(f"create_chain failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/api/chains/{chain_id}")
async def update_chain(chain_id: str, chain: BugChainCreate):
    """Update an existing bug chain."""
    try:
        # Check if exists
        existing = execute_query(
            "SELECT id FROM bug_chains WHERE id = ?",
            (chain_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail=f"Chain {chain_id} not found")

        # Convert tokens list to JSON string if provided
        tokens_json = json.dumps(chain.tokens) if chain.tokens else None

        execute_query(
            """
            UPDATE bug_chains
            SET pattern_label = ?, expected_outcome = ?, missing_signal = ?,
                tokens = ?, status = ?, failure_class_hash = ?
            WHERE id = ?
            """,
            (
                chain.pattern_label,
                chain.expected_outcome,
                chain.missing_signal,
                tokens_json,
                chain.status,
                chain.failure_class_hash,
                chain_id
            )
        )

        logger.info(f"Updated bug chain: {chain_id}")
        return {"success": True, "id": chain_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"update_chain failed for {chain_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/chains/{chain_id}")
async def delete_chain(chain_id: str):
    """Delete a bug chain and its members."""
    try:
        # Check if exists
        existing = execute_query(
            "SELECT id FROM bug_chains WHERE id = ?",
            (chain_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail=f"Chain {chain_id} not found")

        # Delete members first (FK constraint)
        execute_query(
            "DELETE FROM bug_chain_members WHERE chain_id = ?",
            (chain_id,)
        )

        # Delete chain
        execute_query(
            "DELETE FROM bug_chains WHERE id = ?",
            (chain_id,)
        )

        logger.info(f"Deleted bug chain: {chain_id}")
        return {"success": True, "id": chain_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"delete_chain failed for {chain_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/chains/{chain_id}/members")
async def add_chain_member(chain_id: str, member: BugChainMemberAdd):
    """Add a bug to a chain."""
    try:
        # Check chain exists
        chain_exists = execute_query(
            "SELECT id FROM bug_chains WHERE id = ?",
            (chain_id,)
        )
        if not chain_exists:
            raise HTTPException(status_code=404, detail=f"Chain {chain_id} not found")

        # Get bug requirement_id
        bug_rows = execute_query(
            """
            SELECT id
            FROM roadmap_requirements
            WHERE code = ? AND type = 'bug'
            """,
            (member.code,)
        )
        if not bug_rows:
            raise HTTPException(status_code=404, detail=f"Bug {member.code} not found")

        bug_req_id = bug_rows[0]["id"]

        # Insert member (idempotent via UNIQUE constraint)
        try:
            execute_query(
                """
                INSERT INTO bug_chain_members (bug_requirement_id, chain_id, created_by)
                VALUES (?, ?, 'CC')
                """,
                (bug_req_id, chain_id)
            )
        except Exception:
            # Already exists, ignore
            pass

        logger.info(f"Added {member.code} to chain {chain_id}")
        return {"success": True, "chain_id": chain_id, "bug_code": member.code}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"add_chain_member failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/chains/{chain_id}/members/{bug_code}")
async def remove_chain_member(chain_id: str, bug_code: str):
    """Remove a bug from a chain."""
    try:
        # Get bug requirement_id
        bug_rows = execute_query(
            """
            SELECT id
            FROM roadmap_requirements
            WHERE code = ? AND type = 'bug'
            """,
            (bug_code,)
        )
        if not bug_rows:
            raise HTTPException(status_code=404, detail=f"Bug {bug_code} not found")

        bug_req_id = bug_rows[0]["id"]

        # Delete member
        execute_query(
            "DELETE FROM bug_chain_members WHERE bug_requirement_id = ? AND chain_id = ?",
            (bug_req_id, chain_id)
        )

        logger.info(f"Removed {bug_code} from chain {chain_id}")
        return {"success": True, "chain_id": chain_id, "bug_code": bug_code}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"remove_chain_member failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/chains/{source_id}/merge")
async def merge_chains(source_id: str, merge: BugChainMerge):
    """Merge source chain into target chain."""
    try:
        target_id = merge.target

        # Check both exist
        source_exists = execute_query("SELECT id FROM bug_chains WHERE id = ?", (source_id,))
        target_exists = execute_query("SELECT id FROM bug_chains WHERE id = ?", (target_id,))

        if not source_exists:
            raise HTTPException(status_code=404, detail=f"Source chain {source_id} not found")
        if not target_exists:
            raise HTTPException(status_code=404, detail=f"Target chain {target_id} not found")

        # Move all members from source to target (idempotent)
        members = execute_query(
            "SELECT bug_requirement_id FROM bug_chain_members WHERE chain_id = ?",
            (source_id,)
        ) or []

        for m in members:
            bug_req_id = m["bug_requirement_id"]
            try:
                execute_query(
                    """
                    INSERT INTO bug_chain_members (bug_requirement_id, chain_id, created_by)
                    VALUES (?, ?, 'CC')
                    """,
                    (bug_req_id, target_id)
                )
            except Exception:
                # Already exists in target, skip
                pass

        # Delete source chain (members already moved)
        execute_query("DELETE FROM bug_chain_members WHERE chain_id = ?", (source_id,))
        execute_query("DELETE FROM bug_chains WHERE id = ?", (source_id,))

        logger.info(f"Merged chain {source_id} into {target_id}")
        return {"success": True, "source_id": source_id, "target_id": target_id}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"merge_chains failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Admin — POST /api/classifier/seed (MP56-PATCH Gap 1)
# ---------------------------------------------------------------------------

@router.post("/api/classifier/seed")
async def run_seed():
    """
    MP56-PATCH-2: Admin endpoint to seed bug_chains, bug_classifications, bug_chain_members.
    Loads from app/data/mp56_seed_classifier_data.json (baked into container)

    PREREQUISITE: MP56 schema migration must be run first to create bug_chains table.
    """
    logger.info("[SEED] ===== Starting seed endpoint =====")
    try:
        from pathlib import Path
        import json

        # Load export JSON (MP56-PATCH-2: moved to app/data for container deploy)
        json_path = Path(__file__).parent.parent / "data" / "mp56_seed_classifier_data.json"
        logger.info(f"[SEED] Loading JSON from {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"[SEED] Loaded {len(data['bugs'])} bugs, {len(data.get('chains', []))} chains")

        results = {
            "chains_inserted": 0,
            "chains_skipped": 0,
            "bug_classifications_inserted": 0,
            "bug_classifications_skipped": 0,
            "bug_chain_members_inserted": 0,
            "bug_chain_members_skipped": 0,
            "skipped_bug_codes": [],
            "warning": None,
        }

        # Phase 1: Seed bug_chains
        logger.info("[SEED] Phase 1: Seeding bug_chains")
        for chain in data.get("chains", []):
            chain_id = chain["id"]

            # Check if already exists
            existing = execute_query("SELECT id FROM bug_chains WHERE id = ?", (chain_id,))
            if existing:
                logger.info(f"[SEED] Chain {chain_id} already exists, skipping")
                results["chains_skipped"] += 1
                continue

            # Insert chain
            member_codes_json = json.dumps(chain.get("member_requirement_codes", []))

            try:
                execute_query(
                    """
                    INSERT INTO bug_chains (
                        id, pattern_label, expected_outcome,
                        member_requirement_codes, total_occurrences,
                        status, failure_class_hash, first_occurrence_requirement_code,
                        first_occurrence_at, diagnostic_pth, resolution_pth, resolved_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chain_id,
                        chain.get("pattern_label", chain_id),
                        chain.get("expected_outcome", ""),
                        member_codes_json,
                        chain.get("total_occurrences", 0),
                        chain.get("status", "active"),
                        chain.get("failure_class_hash"),
                        chain.get("first_occurrence_requirement_code"),
                        chain.get("first_occurrence_at"),
                        chain.get("diagnostic_pth"),
                        chain.get("resolution_pth"),
                        chain.get("resolved_at"),
                    ),
                    fetch="none"
                )
                logger.info(f"[SEED] Inserted chain {chain_id}")
                results["chains_inserted"] += 1
            except Exception as e:
                logger.error(f"[SEED] Failed to insert chain {chain_id}: {e}")

        # Phase 2: Seed bug_classifications (join table created by migration)
        try:
            logger.info("[SEED] Phase 2: Querying classifications table")
            cls_rows = execute_query("SELECT code, name FROM classifications")
            logger.info(f"[SEED] Got {len(cls_rows)} classification rows")
        except Exception as e:
            logger.error(f"[SEED] Failed to query classifications: {e}")
            return {
                "error": "classifications table not found",
                "detail": str(e),
                "message": "Rename failure_types to classifications first (MP56 migration Phase A.3)"
            }

        cls_mapping = {row["name"].lower(): row["code"] for row in cls_rows}

        for bug in data["bugs"]:
            bug_code = bug["code"]
            logger.info(f"[SEED] Processing bug {bug_code}")
            bug_rows = execute_query(
                "SELECT id FROM roadmap_requirements WHERE code = ? AND type = 'bug'",
                (bug_code,)
            )
            if not bug_rows:
                results["skipped_bug_codes"].append(bug_code)
                logger.info(f"[SEED] Bug {bug_code} not found in DB, skipping")
                continue

            bug_req_id = bug_rows[0]["id"]

            for cls_name in bug.get("classifications", []):
                cls_code = cls_mapping.get(cls_name.lower())
                if not cls_code:
                    # Try normalizing name to code
                    cls_code = cls_name.lower().replace(" ", "_").replace("—", "_").replace("/", "_")
                    if cls_code not in [row["code"] for row in cls_rows]:
                        continue

                logger.info(f"[SEED] Checking existing: bug {bug_code} → cls {cls_code}")
                existing = execute_query(
                    "SELECT id FROM bug_classifications WHERE bug_requirement_id = ? AND classification_code = ?",
                    (bug_req_id, cls_code)
                )
                if existing:
                    results["bug_classifications_skipped"] += 1
                    continue

                logger.info(f"[SEED] Inserting bug_classification: bug {bug_code} → cls {cls_code}, fetch=none")
                execute_query(
                    "INSERT INTO bug_classifications (bug_requirement_id, classification_code, created_by) VALUES (?, ?, 'seed')",
                    (bug_req_id, cls_code),
                    fetch="none"
                )
                logger.info(f"[SEED] Insert successful")
                results["bug_classifications_inserted"] += 1

        # Phase 3: Seed bug_chain_members
        logger.info("[SEED] Phase 3: Seeding bug_chain_members")
        for bug in data["bugs"]:
            bug_code = bug["code"]
            bug_rows = execute_query(
                "SELECT id FROM roadmap_requirements WHERE code = ? AND type = 'bug'",
                (bug_code,)
            )
            if not bug_rows:
                continue

            bug_req_id = bug_rows[0]["id"]
            chain_id = bug.get("bug_chain_id")
            if not chain_id:
                continue

            logger.info(f"[SEED] Checking existing chain member: bug {bug_code} → chain {chain_id}")
            existing = execute_query(
                "SELECT id FROM bug_chain_members WHERE bug_requirement_id = ? AND chain_id = ?",
                (bug_req_id, chain_id)
            )
            if existing:
                results["bug_chain_members_skipped"] += 1
                continue

            try:
                logger.info(f"[SEED] Inserting bug_chain_member: bug {bug_code} → chain {chain_id}, fetch=none")
                execute_query(
                    "INSERT INTO bug_chain_members (bug_requirement_id, chain_id, created_by) VALUES (?, ?, 'seed')",
                    (bug_req_id, chain_id),
                    fetch="none"
                )
                logger.info(f"[SEED] Insert successful")
                results["bug_chain_members_inserted"] += 1
            except Exception as e:
                logger.warning(f"Failed to insert chain member {bug_code} → {chain_id}: {e}")

        # Verification: Query actual counts in database
        try:
            chain_count = execute_query("SELECT COUNT(*) as count FROM bug_chains", fetch="one")
            bc_count = execute_query("SELECT COUNT(*) as count FROM bug_classifications", fetch="one")
            bcm_count = execute_query("SELECT COUNT(*) as count FROM bug_chain_members", fetch="one")

            results["verification"] = {
                "bug_chains_count": chain_count["count"] if chain_count else 0,
                "bug_classifications_count": bc_count["count"] if bc_count else 0,
                "bug_chain_members_count": bcm_count["count"] if bcm_count else 0
            }
        except Exception as e:
            logger.error(f"[SEED] Failed to query verification counts: {e}")

        logger.info(f"[SEED] ===== Seed complete. Results: {results} =====")
        return results

    except Exception as exc:
        logger.error(f"run_seed failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


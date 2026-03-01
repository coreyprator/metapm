"""
Deterministic Lesson Routing (MP-MS3 Phase 5).
POST /api/lessons/apply — reads file from GitHub, inserts lesson, commits via API.
GET /api/lessons/recent — last 20 applied lessons.
"""

import logging
import base64
import hashlib
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
import httpx

from app.core.config import settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()

GITHUB_API = "https://api.github.com"
GITHUB_OWNER = "coreyprator"
GCP_PROJECT = "super-flashcards-475210"
SECRET_NAME = "portfolio-rag-github-token"

# Known repos that are valid targets for lesson routing
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


def _generate_lesson_id() -> str:
    """Generate a unique lesson ID: LL-YYYY-MMDD-NNN."""
    now = datetime.utcnow()
    short = uuid.uuid4().hex[:4].upper()
    return f"LL-{now.strftime('%Y-%m%d')}-{short}"


@router.post("/lessons/apply")
async def apply_lesson(body: dict):
    """Apply a lesson learned by committing directly to GitHub."""
    # Validate required fields
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
    applied_by = body['applied_by']

    # Validate repo
    if target_repo not in KNOWN_REPOS:
        raise HTTPException(status_code=400, detail=f"Unknown repo '{target_repo}'. Known: {sorted(KNOWN_REPOS)}")

    # Validate category
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
            # Step 1: Read file from GitHub
            url = f"{GITHUB_API}/repos/{GITHUB_OWNER}/{target_repo}/contents/{target_file}"
            resp = await client.get(url, headers=headers)

            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"File not found: {target_repo}/{target_file}")
            resp.raise_for_status()

            file_data = resp.json()
            file_sha = file_data['sha']
            content_b64 = file_data['content']
            content = base64.b64decode(content_b64).decode('utf-8')

            # Step 2: Find target section
            if target_section not in content:
                # Extract actual section headers for error message
                headers_found = [line.strip() for line in content.split('\n') if line.strip().startswith('##')]
                raise HTTPException(
                    status_code=400,
                    detail=f"Section '{target_section}' not found in {target_file}. Available sections: {headers_found}"
                )

            # Step 3: Duplicate detection (fuzzy — check if first 60 chars of lesson already exist)
            check_text = lesson_text.strip()[:60]
            if check_text in content:
                return {
                    "already_applied": True,
                    "target_repo": target_repo,
                    "target_file": target_file,
                    "note": "Lesson text already exists in the file. Skipping commit."
                }

            # Step 4: Insert lesson text after section header
            section_idx = content.index(target_section)
            # Find end of the section header line
            newline_idx = content.index('\n', section_idx)
            new_content = content[:newline_idx + 1] + lesson_text + '\n' + content[newline_idx + 1:]

            # Step 5: Commit to GitHub
            short_desc = lesson_text.split('\n')[0][:60].strip('- ')
            commit_msg = f"docs: LL from {source_sprint} — {short_desc}"

            new_content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
            put_resp = await client.put(url, headers=headers, json={
                "message": commit_msg,
                "content": new_content_b64,
                "sha": file_sha,
            })

            if put_resp.status_code not in (200, 201):
                raise HTTPException(
                    status_code=502,
                    detail=f"GitHub commit failed: {put_resp.status_code} {put_resp.text}"
                )

            commit_data = put_resp.json()
            commit_sha = commit_data.get('commit', {}).get('sha', 'unknown')

            # Step 6: Create MetaPM requirement record (type: task, status: closed)
            lesson_id = _generate_lesson_id()
            req_id = str(uuid.uuid4())
            # Find the project ID for metapm or the target repo
            project = execute_query(
                "SELECT id FROM roadmap_projects WHERE code = 'MP' OR name LIKE '%MetaPM%'",
                fetch="one"
            )
            project_id = project['id'] if project else 'proj-mp'

            execute_query("""
                INSERT INTO roadmap_requirements (id, project_id, code, title, description, type, priority, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'task', 'P2', 'closed', GETDATE(), GETDATE())
            """, (req_id, project_id, lesson_id,
                  f"LL: {short_desc}",
                  f"Applied to {target_repo}/{target_file} section {target_section}. Commit: {commit_sha}. Category: {category}. Sprint: {source_sprint}."),
                fetch="none")

            return {
                "applied": True,
                "commit_sha": commit_sha[:7],
                "target_repo": target_repo,
                "target_file": target_file,
                "lesson_id": lesson_id,
                "webhook_triggered": True,
                "metapm_task_id": lesson_id,
                "note": "RAG will re-ingest via webhook. Lesson queryable in ~30 seconds."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lesson apply error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lessons/recent")
async def recent_lessons():
    """Return the last 20 applied lessons."""
    try:
        rows = execute_query("""
            SELECT TOP 20 id, code, title, description, status, created_at
            FROM roadmap_requirements
            WHERE code LIKE 'LL-%'
            ORDER BY created_at DESC
        """, fetch="all") or []

        return {"lessons": [{
            "id": r['id'],
            "lesson_id": r['code'],
            "title": r['title'],
            "description": r.get('description'),
            "status": r['status'],
            "created_at": str(r['created_at']),
        } for r in rows]}
    except Exception as e:
        logger.error(f"Error fetching recent lessons: {e}")
        raise HTTPException(status_code=500, detail=str(e))

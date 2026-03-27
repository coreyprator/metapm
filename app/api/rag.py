"""
Portfolio RAG proxy endpoints (MP-MS3 Phase 4) + MetaPM→RAG sync (PR-009).
Proxies requests to the Portfolio RAG service.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
import httpx

from app.core.config import settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)

router = APIRouter()

RAG_BASE = settings.PORTFOLIO_RAG_URL.rstrip("/")
TIMEOUT = 15.0
SYNC_TIMEOUT = 300.0


ETYMOLOGY_COLLECTIONS = {"etymology", "dcc", "wiktionary"}
SQL_COLLECTIONS = {"portfolio", "metapm", "code", "jazz_theory"}


@router.get("/rag/query")
async def rag_query(
    q: str = Query(..., min_length=1),
    collection: Optional[str] = None,
    n: int = 5,
):
    """Route search by collection.
    etymology/dcc/wiktionary → Portfolio RAG /search/etymology (semantic)
    portfolio/metapm/code/jazz_theory → MetaPM SQL /api/search/knowledge
    No collection → Portfolio RAG /search/etymology (default etymology search)
    """
    if collection and collection in SQL_COLLECTIONS:
        # Route to MetaPM SQL full-text search
        try:
            rows = execute_query(
                """
                SELECT TOP 20
                  'requirement' AS source_type,
                  r.code,
                  r.title,
                  r.description,
                  p.code AS project_code,
                  r.status
                FROM roadmap_requirements r
                JOIN roadmap_projects p ON r.project_id = p.id
                WHERE r.title LIKE ? OR r.description LIKE ?
                UNION ALL
                SELECT TOP 10
                  'compliance_doc' AS source_type,
                  c.id AS code,
                  c.id AS title,
                  c.content_md AS description,
                  c.project_code,
                  c.doc_type AS status
                FROM compliance_docs c
                WHERE c.content_md LIKE ?
                ORDER BY source_type
                """,
                (f"%{q}%", f"%{q}%", f"%{q}%"),
                fetch="all",
            )
            results = [dict(r) for r in rows] if rows else []
            return {"query": q, "collection": collection, "source": "metapm_sql", "total": len(results), "results": results}
        except Exception as e:
            logger.error(f"RAG query SQL fallback error: {e}")
            raise HTTPException(status_code=500, detail=f"SQL search failed: {e}")
    else:
        # Route to Portfolio RAG semantic search (etymology/dcc/wiktionary or default)
        effective_collection = collection if collection in ETYMOLOGY_COLLECTIONS else "etymology"
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    f"{RAG_BASE}/search/etymology",
                    params={"q": q, "collection": effective_collection, "n": n},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            # Fallback to legacy /semantic if /search/etymology not yet deployed
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    resp2 = await client.get(
                        f"{RAG_BASE}/semantic",
                        params={"q": q, "collection": effective_collection, "n": n},
                    )
                    resp2.raise_for_status()
                    return resp2.json()
            except Exception as e2:
                raise HTTPException(status_code=502, detail=f"RAG service error: {e2}")
        except Exception as e:
            logger.error(f"RAG query proxy error: {e}")
            raise HTTPException(status_code=502, detail=f"RAG service error: {e}")


@router.get("/rag/documents")
async def rag_documents(repo: Optional[str] = None, doc_type: Optional[str] = None):
    """Proxy document listing to Portfolio RAG."""
    try:
        params = {}
        if repo:
            params["repo"] = repo
        if doc_type:
            params["doc_type"] = doc_type
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{RAG_BASE}/documents", params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"RAG documents proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"RAG service error: {e}")


@router.get("/rag/latest/{doc_type}")
async def rag_latest(doc_type: str, repo: Optional[str] = None):
    """Proxy latest document query to Portfolio RAG."""
    try:
        params = {}
        if repo:
            params["repo"] = repo
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{RAG_BASE}/latest/{doc_type}", params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"RAG latest proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"RAG service error: {e}")


@router.get("/rag/checkpoints")
async def rag_checkpoints():
    """Proxy checkpoint listing to Portfolio RAG."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{RAG_BASE}/checkpoints")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"RAG checkpoints proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"RAG service error: {e}")


def _write_governance_kv(key: str, value: dict) -> None:
    """Upsert a key/value record in governance_kv table (Amendment E)."""
    import json as _json
    value_json = _json.dumps(value)
    try:
        existing = execute_query(
            "SELECT 1 FROM governance_kv WHERE key_name = ?", (key,), fetch="one"
        )
        if existing:
            execute_query(
                "UPDATE governance_kv SET value_json = ?, updated_at = GETUTCDATE() WHERE key_name = ?",
                (value_json, key), fetch="none"
            )
        else:
            execute_query(
                "INSERT INTO governance_kv (key_name, value_json) VALUES (?, ?)",
                (key, value_json), fetch="none"
            )
    except Exception as e:
        logger.warning(f"governance_kv write failed (non-fatal): {e}")


@router.post("/rag/sync")
async def sync_requirements_to_rag():
    """Sync all MetaPM requirements into Portfolio RAG metapm collection.

    Fetches all requirements from MetaPM DB, builds chunks per SYNC-2 schema,
    and POSTs to Portfolio RAG /ingest/custom with replace_collection=true.
    Called by Cloud Scheduler nightly or manually.
    Amendment E: adds [RAG_SYNC] progress logging + governance_kv status persistence.
    """
    sync_start = datetime.now(timezone.utc)
    logger.info("[RAG_SYNC] Starting — fetching requirements from DB")
    api_key = settings.PORTFOLIO_RAG_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="PORTFOLIO_RAG_API_KEY not configured"
        )

    # Fetch all requirements from DB
    try:
        rows = execute_query("""
            SELECT r.id, r.project_id, r.code, r.title, r.description,
                   r.type, r.priority, r.status, r.target_version,
                   r.sprint_id, r.handoff_id, r.uat_id, r.pth,
                   r.created_at, r.updated_at,
                   p.code as project_code, p.name as project_name
            FROM roadmap_requirements r
            JOIN roadmap_projects p ON r.project_id = p.id
            ORDER BY p.code, r.code
        """, fetch="all")
    except Exception as e:
        logger.error(f"RAG sync DB query failed: {e}")
        raise HTTPException(status_code=500, detail=f"DB query failed: {e}")

    if not rows:
        return {"synced": 0, "collection": "metapm", "timestamp": datetime.now(timezone.utc).isoformat()}

    # Build chunks per SYNC-2 schema
    chunks = []
    for row in rows:
        code = row.get("code", "")
        project_name = row.get("project_name", "")
        title = row.get("title", "")
        status = row.get("status", "")
        priority = row.get("priority", "")
        req_type = row.get("type", "")
        pth = row.get("pth", "")
        description = row.get("description", "")
        created_at = str(row.get("created_at", ""))
        updated_at = str(row.get("updated_at", ""))

        text = (
            f"REQUIREMENT: {code}\n"
            f"PROJECT: {project_name}\n"
            f"TITLE: {title}\n"
            f"STATUS: {status}\n"
            f"PRIORITY: {priority}\n"
            f"TYPE: {req_type}\n"
            f"PTH: {pth}\n"
            f"DESCRIPTION: {description}\n"
            f"CREATED: {created_at}\n"
            f"UPDATED: {updated_at}"
        )

        metadata = {
            "source": "MetaPM",
            "code": code,
            "project": project_name,
            "status": status,
            "priority": priority,
            "pth": pth or "",
            "version": "1.0",
        }

        req_id = row.get("id", code)
        chunks.append({
            "id": f"metapm::{req_id}",
            "content": text,
            "metadata": metadata,
        })

    # POST to Portfolio RAG /ingest/custom in batches of 25
    import asyncio
    batch_size = 25
    total_ingested = 0
    headers = {"Content-Type": "application/json", "x-api-key": api_key}

    try:
        async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                do_replace = i == 0  # only replace on first batch
                payload = {
                    "collection": "metapm",
                    "replace_collection": do_replace,
                    "chunks": batch,
                }
                resp = await client.post(
                    f"{RAG_BASE}/ingest/custom",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()
                total_ingested += result.get("chunks_ingested", len(batch))
                logger.info(f"RAG sync batch {i // batch_size + 1}: {len(batch)} chunks (replace={do_replace})")
                # Pause between batches to avoid rate limits
                if i + batch_size < len(chunks):
                    await asyncio.sleep(2)
    except httpx.HTTPStatusError as e:
        logger.error(f"RAG sync ingest failed at chunk {i}: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"RAG ingest failed at batch {i // batch_size + 1}: {e}"
        )
    except Exception as e:
        logger.error(f"RAG sync error: {e}")
        raise HTTPException(status_code=502, detail=f"RAG service error: {e}")

    logger.info(f"RAG sync complete: {total_ingested} requirements synced to metapm collection")
    req_ingested = total_ingested

    # GROUP 4 (MP-MEGA-005): Sync UAT records (cc_spec, not archived) to metapm collection
    try:
        uat_rows = execute_query("""
            SELECT id, project, sprint_code, pth, version, status,
                   test_cases_json, general_notes, pl_submitted_at, spec_locked_at
            FROM uat_pages
            WHERE spec_source = 'cc_spec' AND status != 'archived'
            ORDER BY spec_locked_at DESC
        """, fetch="all")
    except Exception as e:
        logger.warning(f"RAG sync UAT query failed (non-fatal): {e}")
        uat_rows = []

    if uat_rows:
        uat_chunks = []
        for row in uat_rows:
            tc_json = json.loads(row.get("test_cases_json") or "[]") if row.get("test_cases_json") else []
            tc_lines = "\n".join(
                f"  {tc.get('id','')} [{tc.get('status','pending').upper()}]: {tc.get('title','')} — {tc.get('notes','') or ''}"
                for tc in tc_json
            )
            passed = sum(1 for t in tc_json if t.get("status") == "pass")
            failed = sum(1 for t in tc_json if t.get("status") == "fail")
            text = (
                f"UAT: {row.get('pth','')} | {row.get('project','')} v{row.get('version','')}\n"
                f"Sprint: {row.get('sprint_code','')}\n"
                f"Status: {row.get('status','')}\n"
                f"Results: {passed} passed, {failed} failed\n"
                f"Test cases:\n{tc_lines}\n"
                f"General notes: {row.get('general_notes','') or ''}\n"
                f"URL: https://metapm.rentyourcio.com/uat/{row['id']}"
            )
            uat_chunks.append({
                "id": f"metapm::uat::{row['id']}",
                "content": text,
                "metadata": {
                    "source": "MetaPM-UAT",
                    "pth": row.get("pth") or "",
                    "project": row.get("project") or "",
                    "status": row.get("status") or "",
                    "version": row.get("version") or "",
                },
            })

        try:
            async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
                for i in range(0, len(uat_chunks), batch_size):
                    batch = uat_chunks[i: i + batch_size]
                    payload = {
                        "collection": "metapm",
                        "replace_collection": False,
                        "chunks": batch,
                    }
                    resp = await client.post(
                        f"{RAG_BASE}/ingest/custom",
                        json=payload,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    total_ingested += result.get("chunks_ingested", len(batch))
                    if i + batch_size < len(uat_chunks):
                        await asyncio.sleep(1)
            logger.info(f"RAG sync UAT: {total_ingested - req_ingested} UAT records synced")
        except Exception as e:
            logger.warning(f"RAG sync UAT ingest failed (non-fatal): {e}")

    elapsed = (datetime.now(timezone.utc) - sync_start).total_seconds()
    logger.info(f"[RAG_SYNC] Complete — synced={total_ingested} requirements={req_ingested} "
                f"uats={total_ingested - req_ingested} elapsed={elapsed:.1f}s")
    _write_governance_kv("rag_sync_last_run", {
        "status": "success",
        "synced": total_ingested,
        "synced_requirements": req_ingested,
        "synced_uats": total_ingested - req_ingested,
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": sync_start.isoformat(),
    })
    return {
        "synced": total_ingested,
        "synced_requirements": req_ingested,
        "synced_uats": total_ingested - req_ingested,
        "elapsed_seconds": round(elapsed, 1),
        "collection": "metapm",
        "timestamp": sync_start.isoformat(),
    }


@router.get("/search/knowledge")
async def search_knowledge(q: str = Query(..., min_length=1), limit: int = 20):
    """Full-text search across MetaPM requirements and compliance docs.
    Replaces Portfolio RAG for project knowledge queries. No RAG latency.
    Falls back to LIKE-based search if SQL Server full-text index not enabled.
    """
    limit = min(max(limit, 1), 50)
    results = []

    # Try CONTAINS() full-text search first; fall back to LIKE if FTS not enabled
    try:
        rows = execute_query(
            """
            SELECT TOP 20
              'requirement' AS source_type,
              r.code,
              r.title,
              r.description,
              p.code AS project_code,
              r.status
            FROM roadmap_requirements r
            JOIN roadmap_projects p ON r.project_id = p.id
            WHERE CONTAINS((r.title, r.description), ?)
            UNION ALL
            SELECT TOP 10
              'compliance_doc' AS source_type,
              c.id AS code,
              c.id AS title,
              c.content_md AS description,
              c.project_code,
              c.doc_type AS status
            FROM compliance_docs c
            WHERE CONTAINS(c.content_md, ?)
            ORDER BY source_type
            """,
            (q, q),
            fetch="all",
        )
        results = [dict(r) for r in rows] if rows else []
        search_method = "full_text"
    except Exception as fts_err:
        logger.warning(f"CONTAINS() failed (FTS not enabled?), falling back to LIKE: {fts_err}")
        try:
            # Build per-word OR conditions for better recall on multi-word queries
            words = [w.strip() for w in q.split() if len(w.strip()) >= 2]
            if not words:
                words = [q]
            req_conditions = " OR ".join(
                f"(r.title LIKE ? OR r.description LIKE ?)" for _ in words
            )
            doc_conditions = " OR ".join(f"c.content_md LIKE ?" for _ in words)
            req_params = []
            for w in words:
                req_params.extend([f"%{w}%", f"%{w}%"])
            doc_params = [f"%{w}%" for w in words]
            rows = execute_query(
                f"""
                SELECT TOP 20
                  'requirement' AS source_type,
                  r.code,
                  r.title,
                  r.description,
                  p.code AS project_code,
                  r.status
                FROM roadmap_requirements r
                JOIN roadmap_projects p ON r.project_id = p.id
                WHERE {req_conditions}
                UNION ALL
                SELECT TOP 10
                  'compliance_doc' AS source_type,
                  c.id AS code,
                  c.id AS title,
                  c.content_md AS description,
                  c.project_code,
                  c.doc_type AS status
                FROM compliance_docs c
                WHERE {doc_conditions}
                ORDER BY source_type
                """,
                tuple(req_params + doc_params),
                fetch="all",
            )
            results = [dict(r) for r in rows] if rows else []
            search_method = "like"
        except Exception as like_err:
            logger.error(f"Knowledge search failed: {like_err}")
            raise HTTPException(status_code=500, detail=f"Search failed: {like_err}")

    return {
        "query": q,
        "total": len(results),
        "search_method": search_method,
        "results": results[:limit],
    }


ALLOWED_COLLECTIONS = {"portfolio", "etymology", "code", "jazz_theory", "metapm"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/tools/ingest")
async def tools_ingest(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    collection: str = Form(...),
):
    """Proxy document ingest to Portfolio RAG (MP-053).
    Accepts a file upload (PDF, MD, TXT) or URL. Does not expose the RAG API key to frontend.
    """
    api_key = settings.PORTFOLIO_RAG_API_KEY
    if not api_key:
        raise HTTPException(status_code=503, detail="PORTFOLIO_RAG_API_KEY not configured")

    if collection not in ALLOWED_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid collection. Must be one of: {', '.join(sorted(ALLOWED_COLLECTIONS))}")

    headers = {"x-api-key": api_key}

    if file:
        # Read file content
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 5MB)")

        filename = file.filename or "upload"
        source_id = f"upload/{collection}/{filename}"

        # Decode text content
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be a text-readable format (MD, TXT, PDF not supported for binary decode)")

        # Build a single custom chunk
        chunk = {
            "id": str(uuid.uuid4()),
            "content": text,
            "metadata": {
                "source": source_id,
                "filename": filename,
                "collection": collection,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
        }
        payload = {
            "collection": collection,
            "chunks": [chunk],
            "replace_collection": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{RAG_BASE}/ingest/custom",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"RAG ingest error: {e.response.text}")
        except Exception as e:
            logger.error(f"Tools ingest proxy error: {e}")
            raise HTTPException(status_code=502, detail=f"RAG service error: {e}")

        chunks_ingested = result.get("ingested", result.get("count", 1))
        return {
            "status": "ingested",
            "source_id": source_id,
            "collection": collection,
            "chunks": chunks_ingested,
            "filename": filename,
        }

    elif url:
        # Forward URL ingest request
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{RAG_BASE}/ingest/url",
                    json={"url": url, "collection": collection},
                    headers={**headers, "Content-Type": "application/json"},
                )
                resp.raise_for_status()
                result = resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"RAG ingest error: {e.response.text}")
        except Exception as e:
            logger.error(f"Tools ingest URL proxy error: {e}")
            raise HTTPException(status_code=502, detail=f"RAG service error: {e}")

        return {
            "status": "ingested",
            "source_id": url,
            "collection": collection,
            "chunks": result.get("ingested", result.get("count", 1)),
            "url": url,
        }

    else:
        raise HTTPException(status_code=400, detail="Provide either a file or a URL")

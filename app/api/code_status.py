"""MetaPM code_files freshness endpoint.

MP48 BUG-090: Expose per-app deploy_sha + latest_ingest + file_count so CAI
can verify that each portfolio app's SQL source snapshot is current.
"""

import logging

from fastapi import APIRouter

from app.core.database import execute_query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/code-files/status")
async def code_files_status():
    rows = execute_query(
        """
        SELECT app,
               MAX(deploy_sha)   AS deploy_sha,
               MAX(ingested_at)  AS latest_ingest,
               COUNT(*)          AS file_count
        FROM code_files
        GROUP BY app
        ORDER BY app
        """,
        fetch="all",
    ) or []
    apps = [
        {
            "app": r["app"],
            "deploy_sha": r.get("deploy_sha"),
            "latest_ingest": str(r["latest_ingest"]) if r.get("latest_ingest") else None,
            "file_count": int(r["file_count"]) if r.get("file_count") is not None else 0,
        }
        for r in rows
    ]
    return {"apps": apps}

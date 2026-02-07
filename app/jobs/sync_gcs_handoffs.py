# app/jobs/sync_gcs_handoffs.py
"""
Sync handoffs from GCS bucket to database.
Scans gs://corey-handoff-bridge/*/outbox/*.md and imports to mcp_handoffs.
"""

import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from google.cloud import storage

from app.core.config import settings
from app.core.database import execute_query

logger = logging.getLogger(__name__)

# Project list to scan
PROJECTS = [
    "ArtForge",
    "harmonylab",
    "Super-Flashcards",
    "metapm",
    "Etymython",
    "project-methodology"
]


def parse_handoff_metadata(content: str) -> Dict[str, Any]:
    """
    Parse handoff header to extract metadata.

    Looks for standard header format:
    > **From**: Claude Code (Command Center)
    > **To**: Claude.ai (Architect)
    > **Project**: 🔵 HarmonyLab
    > **Task**: auth-redirect-fix
    > **Timestamp**: 2026-02-07T20:30:00Z
    """
    metadata = {
        'from_entity': None,
        'to_entity': None,
        'project': None,
        'task': None,
        'timestamp': None,
        'direction': 'cc_to_ai',  # default
    }

    patterns = {
        'from_entity': r'\*\*From\*\*:\s*(.+)',
        'to_entity': r'\*\*To\*\*:\s*(.+)',
        'project': r'\*\*Project\*\*:\s*(.+)',
        'task': r'\*\*Task\*\*:\s*(.+)',
        'timestamp': r'\*\*Timestamp\*\*:\s*(.+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            value = match.group(1).strip()
            # Clean up project name (remove emoji prefix)
            if key == 'project':
                # Remove emoji and whitespace: "🔵 HarmonyLab" -> "HarmonyLab"
                value = re.sub(r'^[^\w]+', '', value).strip()
            metadata[key] = value

    # Determine direction based on From field
    if metadata['from_entity']:
        from_lower = metadata['from_entity'].lower()
        if 'claude code' in from_lower or 'command center' in from_lower:
            metadata['direction'] = 'cc_to_ai'
        elif 'claude.ai' in from_lower or 'architect' in from_lower:
            metadata['direction'] = 'ai_to_cc'

    return metadata


def sync_gcs_handoffs() -> Dict[str, Any]:
    """
    Scan GCS bucket and import handoffs to database.
    Returns summary of sync operation.
    """
    bucket_name = settings.GCS_HANDOFF_BUCKET
    summary = {
        'scanned': 0,
        'imported': 0,
        'skipped': 0,
        'errors': [],
        'projects_scanned': []
    }

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        for project in PROJECTS:
            prefix = f"{project}/outbox/"
            summary['projects_scanned'].append(project)

            try:
                blobs = list(bucket.list_blobs(prefix=prefix))

                for blob in blobs:
                    if not blob.name.endswith('.md'):
                        continue

                    summary['scanned'] += 1
                    gcs_path = f"gs://{bucket_name}/{blob.name}"

                    # Check if already imported
                    existing = execute_query("""
                        SELECT id FROM mcp_handoffs WHERE gcs_path = ?
                    """, (gcs_path,), fetch="one")

                    if existing:
                        summary['skipped'] += 1
                        continue

                    # Download and parse content
                    try:
                        content = blob.download_as_text()
                        metadata = parse_handoff_metadata(content)

                        # Use parsed project or fall back to folder name
                        handoff_project = metadata['project'] or project
                        handoff_task = metadata['task'] or blob.name.split('/')[-1].replace('.md', '')

                        # Insert to database
                        execute_query("""
                            INSERT INTO mcp_handoffs
                            (project, task, direction, status, content, source, gcs_path, from_entity, to_entity, created_at)
                            VALUES (?, ?, ?, 'pending', ?, 'gcs', ?, ?, ?, ?)
                        """, (
                            handoff_project,
                            handoff_task,
                            metadata['direction'],
                            content,
                            gcs_path,
                            metadata['from_entity'],
                            metadata['to_entity'],
                            blob.time_created or datetime.utcnow()
                        ), fetch="none")

                        summary['imported'] += 1
                        logger.info(f"Imported handoff: {gcs_path}")

                    except Exception as e:
                        error_msg = f"Error processing {blob.name}: {str(e)}"
                        summary['errors'].append(error_msg)
                        logger.error(error_msg)

            except Exception as e:
                error_msg = f"Error scanning {project}: {str(e)}"
                summary['errors'].append(error_msg)
                logger.error(error_msg)

    except Exception as e:
        error_msg = f"GCS client error: {str(e)}"
        summary['errors'].append(error_msg)
        logger.error(error_msg)

    logger.info(f"GCS sync complete: {summary['imported']} imported, {summary['skipped']} skipped")
    return summary

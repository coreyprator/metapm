#!/usr/bin/env python3
"""
One-time migration: Import all existing GCS handoffs into SQL database.
Run after database schema is updated with new columns (Migration 5).

Usage:
    python scripts/migrations/import_gcs_handoffs.py
"""

import hashlib
import os
import re
import sys
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from google.cloud import storage

from app.core.database import execute_query

# Projects to import
PROJECTS = [
    "ArtForge",
    "harmonylab",
    "Super-Flashcards",
    "metapm",
    "Etymython",
    "project-methodology"
]

# Project name normalization (GCS folder → display name)
PROJECT_DISPLAY = {
    "ArtForge": "ArtForge",
    "harmonylab": "HarmonyLab",
    "Super-Flashcards": "Super-Flashcards",
    "metapm": "MetaPM",
    "Etymython": "Etymython",
    "project-methodology": "project-methodology"
}

BUCKET_NAME = "corey-handoff-bridge"


def parse_handoff_header(content: str) -> dict:
    """Extract metadata from handoff markdown header."""
    metadata = {
        "from_entity": None,
        "to_entity": None,
        "task": None,
        "type": None,
        "priority": None,
        "version": None,
        "title": None,
        "direction": "unknown"
    }

    # Parse header fields
    patterns = {
        "from_entity": r'\*\*From\*\*:\s*(.+)',
        "to_entity": r'\*\*To\*\*:\s*(.+)',
        "task": r'\*\*Task\*\*:\s*(.+)',
        "type": r'\*\*Type\*\*:\s*(.+)',
        "priority": r'\*\*Priority\*\*:\s*(.+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            metadata[key] = match.group(1).strip()

    # Extract title from first H1
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        metadata["title"] = title_match.group(1).strip()

    # Extract version (e.g., v1.4.5, v2.2.1)
    version_match = re.search(r'v(\d+\.\d+\.\d+)', content)
    if version_match:
        metadata["version"] = version_match.group(0)

    # Determine direction based on From field
    if metadata["from_entity"]:
        if "Claude Code" in metadata["from_entity"]:
            metadata["direction"] = "to_claude_ai"
        else:
            metadata["direction"] = "to_cc"

    return metadata


def parse_timestamp_from_filename(filename: str) -> datetime:
    """Extract timestamp from filename like 20260207_180300_task.md"""
    match = re.match(r'(\d{8})_(\d{6})_', filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
    return datetime.now()


def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def generate_summary(content: str) -> str:
    """Extract summary from handoff content."""
    # Try to find Summary section
    summary_match = re.search(r'## Summary\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if summary_match:
        return summary_match.group(1).strip()[:500]

    # Fallback: first paragraph after header
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('---') and i > 5:
            # Found end of header, get next non-empty content
            for j in range(i + 1, min(i + 20, len(lines))):
                if lines[j].strip() and not lines[j].startswith('#'):
                    return lines[j].strip()[:500]

    return content[:500]


def import_handoffs():
    """Main import function."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    imported = 0
    skipped = 0
    errors = 0

    for project_folder in PROJECTS:
        print(f"\n[*] Processing {project_folder}...")

        prefix = f"{project_folder}/outbox/"
        try:
            blobs = list(bucket.list_blobs(prefix=prefix))
        except Exception as e:
            print(f"  [ERROR] Error listing blobs: {e}")
            errors += 1
            continue

        for blob in blobs:
            if not blob.name.endswith('.md'):
                continue

            filename = blob.name.split('/')[-1]

            try:
                # Download content
                content = blob.download_as_text()

                # Generate hash for dedup
                content_hash = generate_content_hash(content)

                # Check if already exists
                existing = execute_query(
                    "SELECT id FROM mcp_handoffs WHERE content_hash = ?",
                    (content_hash,),
                    fetch="one"
                )
                if existing:
                    print(f"  [SKIP]  Skipping (exists): {filename}")
                    skipped += 1
                    continue

                # Parse metadata
                metadata = parse_handoff_header(content)
                created_at = parse_timestamp_from_filename(filename)
                task = metadata["task"] or filename.replace('.md', '').split('_', 2)[-1]
                summary = generate_summary(content)
                project_name = PROJECT_DISPLAY.get(project_folder, project_folder)

                # Insert
                execute_query("""
                    INSERT INTO mcp_handoffs (
                        project, task, title, direction, status,
                        priority, type, content, content_hash, summary,
                        from_entity, to_entity, version,
                        created_at, updated_at,
                        gcs_synced, gcs_url, gcs_synced_at,
                        compliance_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_name,
                    task,
                    metadata["title"],
                    metadata["direction"],
                    "done",  # Existing handoffs are completed
                    metadata["priority"],
                    metadata["type"],
                    content,
                    content_hash,
                    summary,
                    metadata["from_entity"],
                    metadata["to_entity"],
                    metadata["version"],
                    created_at,
                    created_at,
                    1,  # Already in GCS
                    f"gs://{BUCKET_NAME}/{blob.name}",
                    blob.time_created,
                    100  # Full compliance for imported handoffs
                ), fetch="none")

                print(f"  [OK] Imported: {filename}")
                imported += 1

            except Exception as e:
                print(f"  [ERROR] Error: {filename} - {e}")
                errors += 1

    print(f"\n{'='*50}")
    print(f"Import Complete!")
    print(f"  [OK] Imported: {imported}")
    print(f"  [SKIP]  Skipped (duplicates): {skipped}")
    print(f"  [ERROR] Errors: {errors}")
    print(f"{'='*50}")

    # Verification queries
    print("\n[STATS] Verification:")

    # Count by project
    counts = execute_query("""
        SELECT project, COUNT(*) as total
        FROM mcp_handoffs
        GROUP BY project
        ORDER BY total DESC
    """, fetch="all")

    print("\nHandoffs by project:")
    for row in counts or []:
        print(f"  {row['project']}: {row['total']}")

    # Total count
    total = execute_query("SELECT COUNT(*) as cnt FROM mcp_handoffs", fetch="one")
    print(f"\nTotal handoffs in database: {total['cnt'] if total else 0}")


if __name__ == "__main__":
    print("=" * 50)
    print("GCS Handoff Import Script")
    print("=" * 50)
    import_handoffs()

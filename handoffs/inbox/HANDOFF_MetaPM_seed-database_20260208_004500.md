# [MetaPM] 🔴 Seed Database — Import All Existing GCS Handoffs

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔴 MetaPM
> **Task**: seed-database-gcs-import
> **Timestamp**: 2026-02-08T00:45:00Z
> **Priority**: HIGH (Part of Dashboard implementation)
> **Type**: Data Migration

---

## Purpose

Import ALL existing handoffs from GCS bucket into the SQL database so the dashboard shows complete history from day one.

**This is a one-time migration that seeds the database.**

---

## GCS Bucket Structure

```
gs://corey-handoff-bridge/
├── ArtForge/
│   └── outbox/
│       ├── 20260207_200901_priority-action-status.md
│       ├── 20260207_212100_uat-fixes.md
│       └── ...
├── harmonylab/
│   └── outbox/
│       ├── 20260207_175911_v1.4.0-complete.md
│       ├── 20260207_183012_v1.4.1-auth-complete.md
│       ├── 20260207_212052_oauth-complete.md
│       ├── 20260207_233104_v145-progress-fix.md
│       └── ...
├── Super-Flashcards/
│   └── outbox/
│       └── ...
├── metapm/
│   └── outbox/
│       ├── 20260207_180300_phase3-api-testing.md
│       └── ...
├── Etymython/
│   └── outbox/
│       └── ...
└── project-methodology/
    └── outbox/
        ├── 20260207_184002_security-remediation.md
        └── ...
```

---

## Import Script

Create `scripts/migrations/import_gcs_handoffs.py`:

```python
#!/usr/bin/env python3
"""
One-time migration: Import all existing GCS handoffs into SQL database.
Run after database schema is updated with new columns.
"""

import asyncio
import hashlib
import re
from datetime import datetime
from google.cloud import storage
import pyodbc  # or your DB driver

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
        "title": None
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
    else:
        metadata["direction"] = "unknown"
    
    return metadata


def parse_timestamp_from_filename(filename: str) -> datetime:
    """Extract timestamp from filename like 20260207_180300_task.md"""
    match = re.match(r'(\d{8})_(\d{6})_', filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
    return datetime.now()


async def import_handoffs():
    """Main import function."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    
    # Connect to database
    conn = pyodbc.connect(os.environ["DATABASE_CONNECTION_STRING"])
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    errors = 0
    
    for project_folder in PROJECTS:
        print(f"\n📂 Processing {project_folder}...")
        
        prefix = f"{project_folder}/outbox/"
        blobs = list(bucket.list_blobs(prefix=prefix))
        
        for blob in blobs:
            if not blob.name.endswith('.md'):
                continue
            
            filename = blob.name.split('/')[-1]
            
            try:
                # Download content
                content = blob.download_as_text()
                
                # Generate hash for dedup
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                
                # Check if already exists
                cursor.execute(
                    "SELECT id FROM mcp_handoffs WHERE content_hash = ?",
                    (content_hash,)
                )
                if cursor.fetchone():
                    print(f"  ⏭️  Skipping (exists): {filename}")
                    skipped += 1
                    continue
                
                # Parse metadata
                metadata = parse_handoff_header(content)
                created_at = parse_timestamp_from_filename(filename)
                task = metadata["task"] or filename.replace('.md', '').split('_', 2)[-1]
                
                # Generate summary (first 500 chars of content after header)
                summary_match = re.search(r'## Summary\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
                summary = summary_match.group(1).strip()[:500] if summary_match else content[:500]
                
                # Insert
                cursor.execute("""
                    INSERT INTO mcp_handoffs (
                        project, task, title, direction, status,
                        priority, type, content, content_hash, summary,
                        from_entity, to_entity, version,
                        created_at, updated_at,
                        gcs_synced, gcs_url, gcs_synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    PROJECT_DISPLAY.get(project_folder, project_folder),
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
                    blob.time_created
                ))
                
                print(f"  ✅ Imported: {filename}")
                imported += 1
                
            except Exception as e:
                print(f"  ❌ Error: {filename} - {e}")
                errors += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"Import Complete!")
    print(f"  ✅ Imported: {imported}")
    print(f"  ⏭️  Skipped (duplicates): {skipped}")
    print(f"  ❌ Errors: {errors}")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(import_handoffs())
```

---

## Run Instructions

1. **Ensure database schema is updated first** (new columns exist)

2. **Run the import script**:
```bash
cd "G:\My Drive\Code\Python\metapm"
python scripts/migrations/import_gcs_handoffs.py
```

3. **Verify import**:
```sql
SELECT project, COUNT(*) as count 
FROM mcp_handoffs 
GROUP BY project 
ORDER BY count DESC;
```

---

## Expected Results

Based on today's session, expect approximately:

| Project | Estimated Handoffs |
|---------|-------------------|
| HarmonyLab | 10-15 |
| ArtForge | 8-12 |
| project-methodology | 5-8 |
| MetaPM | 3-5 |
| Super-Flashcards | 3-5 |
| Etymython | 2-4 |
| **Total** | **30-50** |

---

## Verification Query

After import, run:

```sql
-- Count by project
SELECT project, COUNT(*) as total,
       SUM(CASE WHEN gcs_synced = 1 THEN 1 ELSE 0 END) as synced
FROM mcp_handoffs
GROUP BY project;

-- Recent handoffs
SELECT TOP 10 project, task, created_at, direction
FROM mcp_handoffs
ORDER BY created_at DESC;

-- Check for any missing content
SELECT COUNT(*) as missing_content
FROM mcp_handoffs
WHERE content IS NULL OR LEN(content) = 0;
```

---

## Definition of Done

- [ ] Import script created
- [ ] Script tested on one project first
- [ ] All 6 projects imported
- [ ] Verification queries pass
- [ ] Dashboard shows historical data
- [ ] No duplicate entries (content_hash check works)

---

*Database seeding — start with complete history*

"""
Handoff Service - Business logic for handoff management
SQL is primary store. GCS is derived backup.
"""

import re
import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.core.database import execute_query

logger = logging.getLogger(__name__)

# Project emoji mapping
PROJECT_EMOJI = {
    'ArtForge': '🟠',
    'HarmonyLab': '🔵',
    'harmonylab': '🔵',
    'Super-Flashcards': '🟡',
    'MetaPM': '🔴',
    'metapm': '🔴',
    'Etymython': '🟣',
    'etymython': '🟣',
    'project-methodology': '🟢',
    'Security': '🔒'
}


def parse_handoff_header(content: str) -> Dict[str, Any]:
    """Parse handoff header to extract metadata."""
    metadata = {
        'from_entity': None,
        'to_entity': None,
        'project': None,
        'task': None,
        'version': None,
        'priority': None,
        'type': None,
        'title': None,
        'direction': None
    }

    patterns = {
        'from_entity': r'\*\*From\*\*:\s*(.+)',
        'to_entity': r'\*\*To\*\*:\s*(.+)',
        'project': r'\*\*Project\*\*:\s*(.+)',
        'task': r'\*\*Task\*\*:\s*(.+)',
        'version': r'\*\*Version\*\*:\s*(.+)',
        'priority': r'\*\*Priority\*\*:\s*(.+)',
        'type': r'\*\*Type\*\*:\s*(.+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Clean up emoji and extra chars
            value = re.sub(r'^[🟠🔵🔴🟡🟣🟢🔒]\s*', '', value)
            metadata[key] = value

    # Extract title from first H1
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        metadata['title'] = title_match.group(1).strip()

    # Determine direction from from_entity
    if metadata['from_entity']:
        from_lower = metadata['from_entity'].lower()
        if 'claude code' in from_lower or 'command center' in from_lower:
            metadata['direction'] = 'cc_to_ai'
        elif 'claude.ai' in from_lower or 'architect' in from_lower:
            metadata['direction'] = 'ai_to_cc'

    return metadata


def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash of content for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def generate_summary(content: str, max_length: int = 200) -> str:
    """Extract summary from content (first paragraph after header)."""
    # Skip header block
    lines = content.split('\n')
    in_header = False
    summary_lines = []

    for line in lines:
        if line.startswith('>'):
            in_header = True
            continue
        if in_header and not line.startswith('>') and line.strip():
            in_header = False
        if not in_header and line.strip() and not line.startswith('#') and not line.startswith('---'):
            summary_lines.append(line.strip())
            if len(' '.join(summary_lines)) > max_length:
                break

    summary = ' '.join(summary_lines)[:max_length]
    if len(summary) == max_length:
        summary = summary.rsplit(' ', 1)[0] + '...'

    return summary


def create_handoff(
    project: str,
    task: str,
    content: str,
    direction: str = 'cc_to_ai',
    git_commit: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new handoff in SQL database."""

    # Parse metadata from content
    metadata = parse_handoff_header(content)

    # Generate content hash for dedup
    content_hash = generate_content_hash(content)

    # Check for duplicate
    existing = execute_query(
        "SELECT id FROM mcp_handoffs WHERE content_hash = ?",
        (content_hash,),
        fetch="one"
    )

    if existing:
        logger.info(f"Handoff already exists with hash {content_hash[:8]}...")
        return {"id": str(existing['id']), "duplicate": True}

    # Generate summary
    summary = generate_summary(content)

    # Use metadata or params
    final_project = metadata.get('project') or project
    final_task = metadata.get('task') or task
    final_direction = metadata.get('direction') or direction

    # Clean project name for consistency
    final_project = final_project.replace('🟠', '').replace('🔵', '').replace('🔴', '').replace('🟡', '').replace('🟣', '').replace('🟢', '').strip()

    # Insert into database
    result = execute_query("""
        INSERT INTO mcp_handoffs (
            project, task, direction, content, content_hash, summary, title,
            from_entity, to_entity, version, priority, type,
            git_commit, status, gcs_synced, compliance_score
        )
        OUTPUT INSERTED.id, INSERTED.created_at
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, 100)
    """, (
        final_project,
        final_task,
        final_direction,
        content,
        content_hash,
        summary,
        metadata.get('title'),
        metadata.get('from_entity'),
        metadata.get('to_entity'),
        metadata.get('version'),
        metadata.get('priority'),
        metadata.get('type'),
        git_commit
    ), fetch="one")

    if result:
        handoff_id = str(result['id'])
        logger.info(f"Created handoff {handoff_id} for {final_project}/{final_task}")
        return {
            "id": handoff_id,
            "project": final_project,
            "task": final_task,
            "direction": final_direction,
            "created_at": result['created_at'].isoformat() if result['created_at'] else None,
            "duplicate": False
        }

    raise Exception("Failed to create handoff")


def get_handoff(handoff_id: str) -> Optional[Dict[str, Any]]:
    """Get a single handoff by ID."""
    result = execute_query(
        "SELECT * FROM mcp_handoffs WHERE id = ?",
        (handoff_id,),
        fetch="one"
    )

    if result:
        return _handoff_to_dict(result)
    return None


def get_handoff_content(handoff_id: str) -> Optional[str]:
    """Get raw content of a handoff."""
    result = execute_query(
        "SELECT content FROM mcp_handoffs WHERE id = ?",
        (handoff_id,),
        fetch="one"
    )
    return result['content'] if result else None


def list_handoffs(
    project: Optional[str] = None,
    status: Optional[str] = None,
    direction: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = 'created_at',
    order: str = 'desc',
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """List handoffs with filtering, sorting, and pagination."""

    conditions = []
    params = []

    if project:
        conditions.append("project = ?")
        params.append(project)

    if status:
        statuses = status.split(',')
        placeholders = ','.join(['?' for _ in statuses])
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)

    if direction:
        conditions.append("direction = ?")
        params.append(direction)

    if search:
        conditions.append("(content LIKE ? OR title LIKE ? OR task LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Validate sort column
    valid_sorts = ['created_at', 'project', 'task', 'status', 'updated_at']
    if sort not in valid_sorts:
        sort = 'created_at'

    order = 'DESC' if order.lower() == 'desc' else 'ASC'

    # Get total count
    count_result = execute_query(
        f"SELECT COUNT(*) as total FROM mcp_handoffs WHERE {where_clause}",
        tuple(params),
        fetch="one"
    )
    total = count_result['total'] if count_result else 0

    # Get paginated results
    offset = (page - 1) * limit

    results = execute_query(f"""
        SELECT * FROM mcp_handoffs
        WHERE {where_clause}
        ORDER BY {sort} {order}
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """, tuple(params) + (offset, limit), fetch="all")

    items = [_handoff_to_dict(r) for r in results] if results else []

    # Calculate compliance summary
    compliance_result = execute_query(f"""
        SELECT
            AVG(CAST(compliance_score AS FLOAT)) as avg_score,
            SUM(CASE WHEN gcs_synced = 1 THEN 1 ELSE 0 END) as synced,
            SUM(CASE WHEN gcs_synced = 0 THEN 1 ELSE 0 END) as pending
        FROM mcp_handoffs WHERE {where_clause}
    """, tuple(params), fetch="one")

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "compliance_summary": {
            "overall": int(compliance_result['avg_score'] or 100) if compliance_result else 100,
            "synced": compliance_result['synced'] or 0 if compliance_result else 0,
            "pending_sync": compliance_result['pending'] or 0 if compliance_result else 0
        }
    }


def get_handoff_stats() -> Dict[str, Any]:
    """Get handoff statistics."""

    # Total count
    total_result = execute_query("SELECT COUNT(*) as total FROM mcp_handoffs", fetch="one")
    total = total_result['total'] if total_result else 0

    # By project
    project_results = execute_query("""
        SELECT project,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
               SUM(CASE WHEN status IN ('processed', 'archived') THEN 1 ELSE 0 END) as done
        FROM mcp_handoffs
        GROUP BY project
    """, fetch="all")

    by_project = {}
    if project_results:
        for r in project_results:
            by_project[r['project']] = {
                'total': r['total'],
                'pending': r['pending'] or 0,
                'done': r['done'] or 0,
                'emoji': PROJECT_EMOJI.get(r['project'], '📦')
            }

    # By direction
    direction_result = execute_query("""
        SELECT direction, COUNT(*) as count
        FROM mcp_handoffs
        GROUP BY direction
    """, fetch="all")

    by_direction = {}
    if direction_result:
        for r in direction_result:
            by_direction[r['direction']] = r['count']

    # This week
    week_result = execute_query("""
        SELECT COUNT(*) as count FROM mcp_handoffs
        WHERE created_at >= DATEADD(day, -7, GETDATE())
    """, fetch="one")
    this_week = week_result['count'] if week_result else 0

    # GCS sync status
    sync_result = execute_query("""
        SELECT
            SUM(CASE WHEN gcs_synced = 1 THEN 1 ELSE 0 END) as synced,
            SUM(CASE WHEN gcs_synced = 0 THEN 1 ELSE 0 END) as pending
        FROM mcp_handoffs
    """, fetch="one")

    return {
        "total": total,
        "by_project": by_project,
        "by_direction": by_direction,
        "this_week": this_week,
        "gcs_sync_status": {
            "synced": sync_result['synced'] or 0 if sync_result else 0,
            "pending": sync_result['pending'] or 0 if sync_result else 0
        }
    }


def update_handoff(handoff_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update handoff fields."""
    allowed_fields = ['status', 'git_commit', 'git_verified', 'gcs_synced', 'gcs_url', 'gcs_synced_at', 'read_at', 'completed_at']

    set_clauses = []
    params = []

    for field in allowed_fields:
        if field in updates:
            set_clauses.append(f"{field} = ?")
            params.append(updates[field])

    if not set_clauses:
        return get_handoff(handoff_id)

    set_clauses.append("updated_at = GETDATE()")
    params.append(handoff_id)

    execute_query(
        f"UPDATE mcp_handoffs SET {', '.join(set_clauses)} WHERE id = ?",
        tuple(params),
        fetch="none"
    )

    return get_handoff(handoff_id)


def generate_log_markdown(project: str) -> str:
    """Generate HANDOFF_LOG.md content from SQL data."""

    handoffs = execute_query("""
        SELECT * FROM mcp_handoffs
        WHERE project = ?
        ORDER BY created_at DESC
    """, (project,), fetch="all")

    md = f"# Handoff Log — {project}\n\n"
    md += f"*Generated from MetaPM SQL database*\n"
    md += f"*Last updated: {datetime.now().isoformat()}*\n\n"
    md += "| Timestamp | Direction | Task | Status | Git | GCS |\n"
    md += "|-----------|-----------|------|--------|-----|-----|\n"

    if handoffs:
        for h in handoffs:
            timestamp = h['created_at'].strftime("%Y-%m-%d %H:%M") if h['created_at'] else 'N/A'
            direction = '→ CC' if h['direction'] == 'ai_to_cc' else '← Claude.ai'
            git = h['git_commit'][:7] if h['git_commit'] else '-'
            gcs = '✓' if h['gcs_synced'] else '○'
            md += f"| {timestamp} | {direction} | {h['task']} | {h['status']} | {git} | {gcs} |\n"
    else:
        md += "| *No handoffs found* | | | | | |\n"

    return md


def _handoff_to_dict(row: Dict) -> Dict[str, Any]:
    """Convert database row to API response dict."""
    return {
        'id': str(row['id']),
        'project': row['project'],
        'task': row['task'],
        'title': row.get('title'),
        'direction': row['direction'],
        'status': row['status'],
        'summary': row.get('summary'),
        'from_entity': row.get('from_entity'),
        'to_entity': row.get('to_entity'),
        'version': row.get('version'),
        'priority': row.get('priority'),
        'type': row.get('type'),
        'git_commit': row.get('git_commit'),
        'git_verified': bool(row.get('git_verified')),
        'gcs_synced': bool(row.get('gcs_synced')),
        'gcs_url': row.get('gcs_url'),
        'compliance_score': row.get('compliance_score', 100),
        'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
        'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
        'emoji': PROJECT_EMOJI.get(row['project'], '📦')
    }

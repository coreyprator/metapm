"""Recover legacy personal projects into roadmap_projects for dashboard visibility.

Non-destructive behavior:
- Reads legacy Projects rows (old dashboard/API model)
- Inserts only missing projects into roadmap_projects
- Never deletes or updates existing roadmap_projects rows

Usage:
  python scripts/recover_personal_projects_to_roadmap.py --dry-run
  python scripts/recover_personal_projects_to_roadmap.py --apply
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Dict, List, Set

from app.core.database import execute_query

PORTFOLIO_CODES = {"AF", "EM", "HL", "MP", "PM", "SF"}
STATUS_MAP = {
    "ACTIVE": "active",
    "COMPLETED": "stable",
    "BLOCKED": "paused",
    "ON_HOLD": "paused",
    "PAUSED": "paused",
    "MAINTENANCE": "maintenance",
    "STABLE": "stable",
}


@dataclass
class LegacyProject:
    project_id: int
    project_code: str
    project_name: str
    description: str
    status: str
    color_code: str | None
    github_url: str | None
    production_url: str | None


def normalize_code(raw: str) -> str:
    if not raw:
        return "PRJ"
    code = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    return (code or "PRJ")[:10]


def make_unique_code(base: str, used_codes: Set[str]) -> str:
    if base not in used_codes:
        return base

    stem = base[:8] if len(base) > 8 else base
    for i in range(1, 100):
        candidate = f"{stem}{i:02d}"[:10]
        if candidate not in used_codes:
            return candidate

    return f"P{len(used_codes):09d}"[:10]


def map_status(raw: str) -> str:
    return STATUS_MAP.get((raw or "").upper(), "active")


def load_legacy_projects() -> List[LegacyProject]:
    rows = execute_query(
        """
        SELECT
            ProjectID,
            ProjectCode,
            ProjectName,
            Description,
            Status,
            ColorCode,
            GitHubURL,
            ProductionURL
        FROM Projects
        ORDER BY ProjectID
        """,
        fetch="all",
    ) or []

    projects: List[LegacyProject] = []
    for row in rows:
        projects.append(
            LegacyProject(
                project_id=int(row.get("ProjectID")),
                project_code=(row.get("ProjectCode") or "").strip(),
                project_name=(row.get("ProjectName") or "").strip(),
                description=(row.get("Description") or "").strip(),
                status=(row.get("Status") or "").strip(),
                color_code=row.get("ColorCode"),
                github_url=row.get("GitHubURL"),
                production_url=row.get("ProductionURL"),
            )
        )
    return projects


def load_roadmap_projects() -> List[dict]:
    return execute_query(
        "SELECT id, code, name FROM roadmap_projects ORDER BY code",
        fetch="all",
    ) or []


def build_inserts(legacy: List[LegacyProject], roadmap: List[dict]) -> List[dict]:
    used_codes = {str(p.get("code") or "").upper() for p in roadmap}
    roadmap_names = {str(p.get("name") or "").strip().lower() for p in roadmap}

    inserts: List[dict] = []
    for project in legacy:
        if not project.project_code:
            continue

        legacy_code_upper = project.project_code.upper()
        if legacy_code_upper in PORTFOLIO_CODES:
            continue

        if project.project_name.strip().lower() in roadmap_names:
            continue

        code_candidate = normalize_code(project.project_code)
        code = make_unique_code(code_candidate, used_codes)
        used_codes.add(code)

        desc_prefix = f"Recovered from legacy Projects table (ProjectID={project.project_id}, ProjectCode={project.project_code})."
        description = project.description or ""
        merged_desc = f"{desc_prefix} {description}".strip()

        inserts.append(
            {
                "id": f"legacy-{project.project_id}",
                "code": code,
                "name": project.project_name[:100] if project.project_name else f"Legacy Project {project.project_id}",
                "emoji": "📁",
                "color": project.color_code,
                "current_version": None,
                "status": map_status(project.status),
                "repo_url": project.github_url,
                "deploy_url": project.production_url,
                "description": merged_desc,
                "legacy_code": project.project_code,
                "legacy_id": project.project_id,
            }
        )

    return inserts


def apply_inserts(inserts: List[dict]) -> int:
    created = 0
    for item in inserts:
        exists = execute_query(
            "SELECT 1 as ok FROM roadmap_projects WHERE id = ? OR code = ?",
            (item["id"], item["code"]),
            fetch="one",
        )
        if exists:
            continue

        execute_query(
            """
            INSERT INTO roadmap_projects (id, code, name, emoji, color, current_version, status, repo_url, deploy_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["code"],
                item["name"],
                item["emoji"],
                item["color"],
                item["current_version"],
                item["status"],
                item["repo_url"],
                item["deploy_url"],
            ),
            fetch="none",
        )
        created += 1

    return created


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Persist inserts")
    parser.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    args = parser.parse_args()

    if args.apply and args.dry_run:
        print("Choose either --apply or --dry-run, not both.")
        return 2

    do_apply = args.apply

    legacy = load_legacy_projects()
    roadmap = load_roadmap_projects()
    inserts = build_inserts(legacy, roadmap)

    print(f"Legacy projects found: {len(legacy)}")
    print(f"Roadmap projects before: {len(roadmap)}")
    print(f"Candidates to recover: {len(inserts)}")

    for item in inserts[:20]:
        print(f"  - {item['code']}: {item['name']} (from {item['legacy_code']}/{item['legacy_id']})")
    if len(inserts) > 20:
        print(f"  ... {len(inserts) - 20} more")

    if not do_apply:
        print("Dry-run complete. Re-run with --apply to persist.")
        return 0

    created = apply_inserts(inserts)
    after = load_roadmap_projects()
    print(f"Created: {created}")
    print(f"Roadmap projects after: {len(after)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

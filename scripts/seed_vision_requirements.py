"""Seed missing Portfolio Vision requirements into MetaPM roadmap API.

Usage:
    python scripts/seed_vision_requirements.py --api-base https://metapm.rentyourcio.com
"""

from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TARGET_NEW_IDS = {
    "HL-014", "HL-015", "HL-016", "HL-017", "HL-018",
    "SF-007", "SF-008", "SF-009", "SF-010", "SF-011", "SF-012", "SF-013",
    "AF-007", "AF-008", "AF-009", "AF-010", "AF-011", "AF-012", "AF-013", "AF-014", "AF-015",
    "EM-012",
    "MP-009", "MP-010", "MP-011", "MP-012", "MP-013", "MP-014", "MP-015", "MP-016", "MP-017",
}

# Safeguard: this script is additive-only and intentionally never mutates roadmap_projects.
# Personal/non-portfolio projects can coexist in roadmap_projects and must be preserved.
PORTFOLIO_PROJECT_CODES = {"AF", "EM", "HL", "MP", "PM", "SF"}

STATUS_FORCE_DONE = {"EM-009", "EM-010", "EM-006"}

ROW_PATTERN = re.compile(r"^\|\s*([A-Z]{2}-\d{3})\s*\|\s*([^|]+?)\s*\|\s*(P[123])\s*\|\s*([^|]+?)\s*\|", re.IGNORECASE)


def _http_json(method: str, url: str, payload: dict | None = None) -> dict:
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = Request(url=url, data=body, method=method.upper(), headers=headers)
    try:
        with urlopen(req, timeout=30) as response:
            data = response.read().decode("utf-8")
            return json.loads(data) if data else {}
    except HTTPError as err:
        body = ""
        try:
            body = err.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {err.code} for {method} {url}: {body}") from err


def _normalize_status(raw: str) -> str:
    value = (raw or "").strip().lower()
    if "done" in value or value == "exists":
        return "done"
    if value == "partial":
        return "in_progress"
    if value in {"backlog", "planned", "in_progress", "uat", "needs_fixes", "done"}:
        return value
    return "backlog"


def _infer_type(title: str) -> str:
    lower = title.lower()
    if "fix" in lower or "bug" in lower:
        return "bug"
    if "feature" in lower or "mode" in lower or "dashboard" in lower:
        return "feature"
    if "enhance" in lower or "refine" in lower:
        return "enhancement"
    return "task"


def parse_framework_requirements(framework_path: Path) -> Dict[str, dict]:
    lines = framework_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    rows: Dict[str, dict] = {}

    for line in lines:
        match = ROW_PATTERN.match(line)
        if not match:
            continue
        req_id, title, priority, status = match.groups()
        rows[req_id] = {
            "code": req_id,
            "title": title.strip(),
            "priority": priority.strip().upper(),
            "status": _normalize_status(status),
            "project_code": req_id.split("-")[0],
            "type": _infer_type(title),
        }

    return rows


def seed(api_base: str, framework_path: Path) -> Tuple[int, int]:
    projects = _http_json("GET", f"{api_base}/api/roadmap/projects?limit=100&offset=0").get("projects", [])
    project_by_code = {p["code"]: p for p in projects if "code" in p and "id" in p}

    missing_portfolio = sorted(PORTFOLIO_PROJECT_CODES - set(project_by_code.keys()))
    if missing_portfolio:
        raise RuntimeError(
            "Missing required portfolio roadmap projects; aborting additive seed: "
            + ", ".join(missing_portfolio)
        )

    extra_codes = sorted(set(project_by_code.keys()) - PORTFOLIO_PROJECT_CODES)
    if extra_codes:
        print(
            "INFO: Preserving non-portfolio roadmap projects during seed: "
            + ", ".join(extra_codes)
        )

    existing_requirements = _http_json("GET", f"{api_base}/api/roadmap/requirements?limit=100&offset=0").get("requirements", [])
    existing_ids = {r["code"] for r in existing_requirements}

    framework_rows = parse_framework_requirements(framework_path)

    created = 0
    for req_id in sorted(TARGET_NEW_IDS):
        if req_id in existing_ids:
            continue
        row = framework_rows.get(req_id)
        if not row:
            print(f"WARN: {req_id} not found in framework file")
            continue

        project = project_by_code.get(row["project_code"])
        if not project:
            print(f"WARN: Project code {row['project_code']} not found in API projects")
            continue

        payload = {
            "id": str(uuid.uuid4()),
            "project_id": project["id"],
            "code": row["code"],
            "title": row["title"],
            "description": None,
            "type": row["type"],
            "priority": row["priority"],
            "status": row["status"],
            "target_version": project.get("current_version"),
        }
        _http_json("POST", f"{api_base}/api/roadmap/requirements", payload)
        created += 1
        print(f"CREATED {req_id}: {row['title']}")

    # Refresh and force status updates for completed Etymython items
    requirements = _http_json("GET", f"{api_base}/api/roadmap/requirements?limit=100&offset=0").get("requirements", [])
    by_code = {r["code"]: r for r in requirements}

    updated = 0
    for req_id in sorted(STATUS_FORCE_DONE):
        req = by_code.get(req_id)
        if not req:
            print(f"WARN: Required status update target missing: {req_id}")
            continue
        if req.get("status") == "done":
            continue

        _http_json("PUT", f"{api_base}/api/roadmap/requirements/{req['id']}", {"status": "done"})
        updated += 1
        print(f"UPDATED {req_id} -> done")

    final_reqs = _http_json("GET", f"{api_base}/api/roadmap/requirements?limit=100&offset=0").get("requirements", [])
    print(f"Total requirements now: {len(final_reqs)}")
    return created, updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="https://metapm.rentyourcio.com")
    parser.add_argument(
        "--framework-path",
        default=str(Path(__file__).resolve().parents[2] / "project-methodology" / "Portfolio_Vision_Framework_v3_FINAL_2026-02-16.md"),
    )
    args = parser.parse_args()

    framework_path = Path(args.framework_path)
    if not framework_path.exists():
        print(f"Framework file not found: {framework_path}")
        return 1

    try:
        created, updated = seed(args.api_base.rstrip("/"), framework_path)
        print(f"Done. Created={created}, Updated={updated}")
        return 0
    except (HTTPError, URLError) as err:
        print(f"HTTP error: {err}")
        return 2
    except Exception as err:
        print(f"Error: {err}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

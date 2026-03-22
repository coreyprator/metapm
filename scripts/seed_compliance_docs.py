"""Seed compliance documents into MetaPM compliance_docs table via MCP tools endpoint.

MC01 — seeds Bootstrap, CAI standards, and all PK.md files.

Usage:
    python scripts/seed_compliance_docs.py --api-base https://metapm.rentyourcio.com --api-key <key>

API key is fetched from Secret Manager if not provided:
    gcloud secrets versions access latest --secret=metapm-api-key --project=super-flashcards-475210
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Repo root — two levels up from scripts/
REPO_ROOT = Path(__file__).parent.parent
PM_ROOT = REPO_ROOT.parent / "project-methodology"

DOCS_TO_SEED = [
    {
        "doc_id": "bootstrap",
        "doc_type": "bootstrap",
        "project_code": None,
        "path": PM_ROOT / "templates" / "CC_Bootstrap_v1.md",
        "version": "BOOT-1.5.18-BA07",
        "checkpoint": "BOOT-1.5.18-BA07",
    },
    {
        "doc_id": "cai-outbound",
        "doc_type": "cai_standard",
        "project_code": None,
        "path": PM_ROOT / "docs" / "CAI_Outbound_CC_Prompt_Standard.md",
        "version": "v1.3",
        "checkpoint": "CAI-OUT-1.3",
    },
    {
        "doc_id": "cai-inbound",
        "doc_type": "cai_standard",
        "project_code": None,
        "path": PM_ROOT / "docs" / "CAI_Inbound_CC_Handoff_Standard.md",
        "version": "v1.2",
        "checkpoint": "CAI-IN-1.2",
    },
    {
        "doc_id": "pk-metapm",
        "doc_type": "pk",
        "project_code": "proj-mp",
        "path": REPO_ROOT / "PROJECT_KNOWLEDGE.md",
        "version": "v2.38.3",
        "checkpoint": "MP-PK-2383",
    },
    {
        "doc_id": "pk-sf",
        "doc_type": "pk",
        "project_code": "proj-sf",
        "path": REPO_ROOT.parent / "super-flashcards" / "PROJECT_KNOWLEDGE.md",
        "version": "v3.4.2",
        "checkpoint": "SF-PK-342",
    },
    {
        "doc_id": "pk-artforge",
        "doc_type": "pk",
        "project_code": "proj-af",
        "path": REPO_ROOT.parent / "artforge" / "PROJECT_KNOWLEDGE.md",
        "version": "v2.13.0",
        "checkpoint": "AF-PK-2130",
    },
    {
        "doc_id": "pk-harmonylab",
        "doc_type": "pk",
        "project_code": "proj-hl",
        "path": REPO_ROOT.parent / "harmonylab" / "PROJECT_KNOWLEDGE.md",
        "version": "v2.17.1",
        "checkpoint": "HL-PK-2171",
    },
    {
        "doc_id": "pk-etymython",
        "doc_type": "pk",
        "project_code": "proj-em",
        "path": REPO_ROOT.parent / "etymython" / "PROJECT_KNOWLEDGE.md",
        "version": "v0.8.2",
        "checkpoint": "EM-PK-082",
    },
    {
        "doc_id": "pk-portfolio-rag",
        "doc_type": "pk",
        "project_code": "PR",
        "path": REPO_ROOT.parent / "portfolio-rag" / "PROJECT_KNOWLEDGE.md",
        "version": "v2.7.6",
        "checkpoint": "PR-PK-276",
    },
    {
        "doc_id": "pk-personal-assistant",
        "doc_type": "pk",
        "project_code": "proj-pa",
        "path": REPO_ROOT.parent / "personal-assistant" / "PROJECT_KNOWLEDGE.md",
        "version": "v1.5.2",
        "checkpoint": "PA-PK-152",
    },
    {
        "doc_id": "pk-project-methodology",
        "doc_type": "pk",
        "project_code": "proj-pm",
        "path": PM_ROOT / "PROJECT_KNOWLEDGE.md",
        "version": "v1.0",
        "checkpoint": "PM-PK-100",
    },
]


def call_mcp_tool(api_base: str, api_key: str, tool_name: str, arguments: dict) -> dict:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }).encode()
    req = Request(
        f"{api_base}/mcp-tools",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    with urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
    content = body.get("result", {}).get("content", [{}])
    return json.loads(content[0].get("text", "{}"))


def main():
    parser = argparse.ArgumentParser(description="Seed compliance docs into MetaPM")
    parser.add_argument("--api-base", default="https://metapm.rentyourcio.com")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Print what would be seeded without posting")
    args = parser.parse_args()

    results = {"seeded": [], "skipped": [], "errors": []}

    for doc in DOCS_TO_SEED:
        path: Path = doc["path"]
        if not path.exists():
            print(f"  SKIP {doc['doc_id']} — file not found: {path}")
            results["skipped"].append(doc["doc_id"])
            continue

        content = path.read_text(encoding="utf-8")
        print(f"  {'DRY-RUN' if args.dry_run else 'SEED'} {doc['doc_id']} — {len(content)} chars")

        if args.dry_run:
            results["seeded"].append(doc["doc_id"])
            continue

        try:
            result = call_mcp_tool(args.api_base, args.api_key, "update_compliance_doc", {
                "doc_id": doc["doc_id"],
                "doc_type": doc["doc_type"],
                "project_code": doc["project_code"],
                "content_md": content,
                "version": doc["version"],
                "checkpoint": doc["checkpoint"],
                "updated_by": "seed_script",
            })
            if "error" in result:
                print(f"    ERROR: {result['error']}")
                results["errors"].append(doc["doc_id"])
            else:
                print(f"    {result['status'].upper()} — {result['content_length']} chars stored")
                results["seeded"].append(doc["doc_id"])
        except Exception as e:
            print(f"    EXCEPTION: {e}")
            results["errors"].append(doc["doc_id"])

    print()
    print(f"Seeded: {len(results['seeded'])}  Skipped: {len(results['skipped'])}  Errors: {len(results['errors'])}")
    if results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

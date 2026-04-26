"""
MP56 Phase E - Seed Bug Classifier data from prototype export

Populates:
1. bug_chains table (3 chains from prototype)
2. bug_classifications join table (M:N bug→classifications)
3. bug_chain_members join table (M:N bug→chains)

Input: app/handoffs/MP56_bug_classifier/metapm-classifier-export-2026-04-25.json
"""

import json
import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import execute_query


def load_export():
    """Load the prototype export JSON."""
    json_path = Path(__file__).parent.parent / "app" / "handoffs" / "MP56_bug_classifier" / "metapm-classifier-export-2026-04-25.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_bug_req_id(bug_code):
    """Get roadmap_requirements.id for a bug code."""
    rows = execute_query(
        "SELECT id FROM roadmap_requirements WHERE code = ? AND type = 'bug'",
        (bug_code,)
    )
    return rows[0]["id"] if rows else None


def get_classification_code(name):
    """
    Map prototype classification name to DB classification code.
    Prototype used display names; DB uses codes.
    """
    # Build mapping from name (case-insensitive) to code
    cls_rows = execute_query("SELECT code, name FROM classifications")
    mapping = {row["name"].lower(): row["code"] for row in cls_rows}

    # Try exact match first
    if name.lower() in mapping:
        return mapping[name.lower()]

    # Fallback: normalize name to code-like format
    code = name.lower().replace(" ", "_").replace("—", "_").replace("/", "_")
    if code in [row["code"] for row in cls_rows]:
        return code

    print(f"WARNING: Classification '{name}' not found in DB, skipping")
    return None


def seed_chains(chains):
    """Insert bug chains."""
    for chain in chains:
        chain_id = chain["id"]

        # Check if already exists
        existing = execute_query("SELECT id FROM bug_chains WHERE id = ?", (chain_id,))
        if existing:
            print(f"Chain {chain_id} already exists, skipping")
            continue

        # Insert chain
        member_codes_json = json.dumps(chain.get("member_requirement_codes", []))
        tokens_json = json.dumps(chain.get("tokens", []))

        execute_query(
            """
            INSERT INTO bug_chains (
                id, pattern_label, expected_outcome, missing_signal,
                tokens, member_requirement_codes, total_occurrences,
                status, failure_class_hash, first_occurrence_requirement_code,
                first_occurrence_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chain_id,
                chain.get("pattern_label", chain_id),
                chain.get("expected_outcome", ""),
                chain.get("missing_signal", ""),
                tokens_json,
                member_codes_json,
                chain.get("total_occurrences", 0),
                chain.get("status", "active"),
                chain.get("failure_class_hash"),
                chain.get("first_occurrence_requirement_code"),
                chain.get("first_occurrence_at"),
            )
        )
        print(f"✓ Inserted chain {chain_id}")


def seed_bug_classifications(bugs):
    """Populate bug_classifications join table."""
    inserted = 0
    skipped = 0

    for bug in bugs:
        bug_code = bug["code"]
        bug_req_id = get_bug_req_id(bug_code)

        if not bug_req_id:
            print(f"WARNING: Bug {bug_code} not found in roadmap_requirements, skipping")
            continue

        for cls_name in bug.get("classifications", []):
            cls_code = get_classification_code(cls_name)
            if not cls_code:
                continue

            # Check if already exists
            existing = execute_query(
                "SELECT id FROM bug_classifications WHERE bug_requirement_id = ? AND classification_code = ?",
                (bug_req_id, cls_code)
            )
            if existing:
                skipped += 1
                continue

            # Insert
            execute_query(
                "INSERT INTO bug_classifications (bug_requirement_id, classification_code, created_by) VALUES (?, ?, 'seed')",
                (bug_req_id, cls_code)
            )
            inserted += 1

    print(f"✓ bug_classifications: {inserted} inserted, {skipped} skipped")


def seed_bug_chain_members(bugs):
    """Populate bug_chain_members join table."""
    inserted = 0
    skipped = 0

    for bug in bugs:
        bug_code = bug["code"]
        bug_req_id = get_bug_req_id(bug_code)

        if not bug_req_id:
            continue

        # Prototype has single bug_chain_id string; production supports array bug_chain_ids
        chain_id = bug.get("bug_chain_id")
        if not chain_id:
            continue

        # Check if already exists
        existing = execute_query(
            "SELECT id FROM bug_chain_members WHERE bug_requirement_id = ? AND chain_id = ?",
            (bug_req_id, chain_id)
        )
        if existing:
            skipped += 1
            continue

        # Insert
        try:
            execute_query(
                "INSERT INTO bug_chain_members (bug_requirement_id, chain_id, created_by) VALUES (?, ?, 'seed')",
                (bug_req_id, chain_id)
            )
            inserted += 1
        except Exception as e:
            print(f"WARNING: Failed to insert chain member {bug_code} → {chain_id}: {e}")

    print(f"✓ bug_chain_members: {inserted} inserted, {skipped} skipped")


def main():
    print("=== MP56 Seed Classifier Data ===\n")

    data = load_export()

    print(f"Loaded: {len(data['bugs'])} bugs, {len(data['chains'])} chains, {len(data['classifications'])} classifications\n")

    # Phase 1: Seed chains
    print("Phase 1: Seeding bug chains...")
    seed_chains(data["chains"])

    # Phase 2: Seed bug_classifications join table
    print("\nPhase 2: Seeding bug_classifications join table...")
    seed_bug_classifications(data["bugs"])

    # Phase 3: Seed bug_chain_members join table
    print("\nPhase 3: Seeding bug_chain_members join table...")
    seed_bug_chain_members(data["bugs"])

    print("\n=== Seed complete ===")


if __name__ == "__main__":
    main()

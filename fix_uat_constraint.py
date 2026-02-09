#!/usr/bin/env python3
"""
Fix uat_results status constraint to allow 'pending'.
Run this manually if the migration doesn't run at startup.
"""

import os
import sys
import pyodbc

# Connection parameters - use Cloud SQL public IP
SERVER = os.getenv("SQL_SERVER", "35.224.242.223")
DATABASE = os.getenv("SQL_DATABASE", "MetaPM")
USERNAME = os.getenv("SQL_USER", "sqlserver")
PASSWORD = os.getenv("SQL_PASSWORD", "")

def main():
    if not PASSWORD:
        print("ERROR: SQL_PASSWORD environment variable not set")
        print("Usage: SQL_PASSWORD='your-password' python fix_uat_constraint.py")
        sys.exit(1)

    # Build connection string
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER},1433;"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
    )

    print(f"Connecting to {SERVER}/{DATABASE}...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Check if constraint already allows 'pending'
    print("\n=== Checking current constraint ===")
    cursor.execute("""
        SELECT name, definition
        FROM sys.check_constraints
        WHERE parent_object_id = OBJECT_ID('uat_results')
          AND definition LIKE '%status%'
    """)
    row = cursor.fetchone()
    if row:
        print(f"Current constraint: {row[0]}")
        print(f"Definition: {row[1]}")

        if 'pending' in row[1].lower():
            print("\nConstraint already allows 'pending'. No changes needed.")
            return
    else:
        print("No status constraint found on uat_results table")
        return

    # Drop the existing constraint
    print("\n=== Dropping old constraint ===")
    constraint_name = row[0]
    cursor.execute(f"ALTER TABLE uat_results DROP CONSTRAINT [{constraint_name}]")
    print(f"Dropped constraint: {constraint_name}")

    # Add new constraint with 'pending'
    print("\n=== Adding new constraint ===")
    cursor.execute("""
        ALTER TABLE uat_results
        ADD CONSTRAINT CK_uat_results_status
        CHECK (status IN ('passed', 'failed', 'pending'))
    """)
    print("Added new constraint: CK_uat_results_status")

    conn.commit()
    cursor.close()
    conn.close()
    print("\n=== Fix complete! ===")


if __name__ == "__main__":
    main()

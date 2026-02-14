import pyodbc

# Hardcoded password for testing
dbpass = "Sf2026_t6Q8AMrd15FLOueIHnYC"

connstr = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=35.224.242.223;DATABASE=MetaPM;UID=sqlserver;PWD={dbpass};TrustServerCertificate=yes;"

try:
    conn = pyodbc.connect(connstr)
    cursor = conn.cursor()

    # Test the exact query that fails
    print("Testing exact failing query...")
    cursor.execute("""
        SELECT u.id, u.handoff_id, u.status, u.total_tests,
               u.passed, u.failed, u.notes_count, u.tested_by,
               u.tested_at, u.results_text,
               h.project, h.version
        FROM uat_results u
        JOIN mcp_handoffs h ON u.handoff_id = h.id
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """, (0, 10))
    rows = cursor.fetchall()
    print(f"SUCCESS: Got {len(rows)} rows")
    if rows:
        print(f"First row keys: {list(rows[0].keys())}")
        print(f"First row: id={rows[0]['id']}, handoff_id={rows[0]['handoff_id']}, project={rows[0]['project']}")

    conn.close()
except Exception as e:
    import traceback
    print(f"FAILED: {e}")
    traceback.print_exc()

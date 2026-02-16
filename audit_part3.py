"""Part 3: Investigate handoff linkage and UAT status"""
import pyodbc
import sys

pw = sys.argv[1]
# REDACTED: Connection string removed for security (GitGuardian alert resolved)
# Usage: conn = pyodbc.connect(f'DRIVER={{...}};SERVER={{server}};DATABASE={{db}};UID={{user}};PWD={{password}};...')
conn = pyodbc.connect(f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={{server}};DATABASE={{db}};UID={{user}};PWD={pw};TrustServerCertificate=yes;')
cursor = conn.cursor()

# 1. Schema overview
print('=== RELEVANT TABLES ===')
cursor.execute("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_NAME LIKE '%handoff%' OR TABLE_NAME LIKE '%requirement%' 
       OR TABLE_NAME LIKE '%roadmap%' OR TABLE_NAME LIKE '%uat%'
    ORDER BY TABLE_NAME
""")
for row in cursor.fetchall():
    print(f'  {row[0]}')

# 2. roadmap_handoffs junction table
print('\n=== ROADMAP_HANDOFFS JUNCTION TABLE ===')
cursor.execute('SELECT COUNT(*) FROM roadmap_handoffs')
count = cursor.fetchone()[0]
print(f'  Rows: {count}')
if count > 0:
    cursor.execute('SELECT * FROM roadmap_handoffs')
    for row in cursor.fetchall():
        print(f'  {row}')
else:
    print('  EMPTY — no handoffs linked to requirements!')

# 3. roadmap_handoffs schema
print('\n=== ROADMAP_HANDOFFS SCHEMA ===')
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'roadmap_handoffs'
    ORDER BY ORDINAL_POSITION
""")
for row in cursor.fetchall():
    print(f'  {row[0]:20s} {row[1]:15s} len={str(row[2]):5s} nullable={row[3]}')

# 4. MCP Handoffs
print('\n=== MCP_HANDOFFS (all) ===')
cursor.execute("""
    SELECT id, project, title, status, uat_status, direction, created_at 
    FROM mcp_handoffs ORDER BY created_at DESC
""")
handoffs = cursor.fetchall()
print(f'  Total: {len(handoffs)}')
for row in handoffs:
    hid = str(row[0])[:8]
    title = (row[2] or 'N/A')[:50]
    project = str(row[1] or 'N/A')
    status = str(row[3] or 'N/A')
    uat = str(row[4] or 'N/A')
    created = str(row[6] or 'N/A')[:19]
    print(f'  {hid}... [{status:12s}] {project:15s} {title:50s} uat:{uat:8s} {created}')

# 5. UAT Results
print('\n=== UAT_RESULTS ===')
cursor.execute("""
    SELECT id, handoff_id, status, total_tests, passed, failed, tested_at 
    FROM uat_results ORDER BY tested_at DESC
""")
uats = cursor.fetchall()
print(f'  Total: {len(uats)}')
for row in uats:
    uid = str(row[0])[:8]
    hid = str(row[1])[:8]
    print(f'  {uid}... handoff={hid}... status={str(row[2]):8s} {row[4]}/{row[3]} pass/total  {str(row[6])[:19]}')

# 6. Handoff requests (lifecycle)
print('\n=== HANDOFF_REQUESTS ===')
cursor.execute('SELECT COUNT(*) FROM handoff_requests')
hr_count = cursor.fetchone()[0]
print(f'  Total: {hr_count}')
if hr_count > 0:
    cursor.execute("""
        SELECT id, project, roadmap_id, title, status, created_at 
        FROM handoff_requests ORDER BY created_at DESC
    """)
    for row in cursor.fetchall():
        print(f'  {row[0]:10s} {str(row[1]):15s} roadmap={str(row[2]):15s} {row[3][:40]:40s} [{row[4]}]')

# 7. Handoff completions
print('\n=== HANDOFF_COMPLETIONS ===')
cursor.execute('SELECT COUNT(*) FROM handoff_completions')
hc_count = cursor.fetchone()[0]
print(f'  Total: {hc_count}')

# 8. HO-P1Q3 handoff details
print('\n=== HO-P1Q3 HANDOFF (4AAC803A...) ===')
cursor.execute("""
    SELECT id, project, title, status, uat_status, uat_passed, uat_failed, uat_date,
           direction, created_at, updated_at
    FROM mcp_handoffs 
    WHERE id = '4AAC803A-B062-44D5-8F3C-24E7AA35E21E'
""")
row = cursor.fetchone()
if row:
    print(f'  ID: {row[0]}')
    print(f'  Project: {row[1]}')
    print(f'  Title: {row[2]}')
    print(f'  Status: {row[3]}')
    print(f'  UAT Status: {row[4]}')
    print(f'  UAT Passed/Failed: {row[5]}/{row[6]}')
    print(f'  UAT Date: {row[7]}')
    print(f'  Direction: {row[8]}')
    print(f'  Created: {row[9]}')
    print(f'  Updated: {row[10]}')
else:
    print('  NOT FOUND')

# 9. Requirements that have handoff_id set
print('\n=== REQUIREMENTS WITH HANDOFF_ID ===')
cursor.execute("""
    SELECT code, title, handoff_id, uat_id 
    FROM roadmap_requirements 
    WHERE handoff_id IS NOT NULL OR uat_id IS NOT NULL
""")
linked = cursor.fetchall()
print(f'  Total with links: {len(linked)}')
for row in linked:
    print(f'  {row[0]} {row[1][:40]} handoff={row[2]} uat={row[3]}')

# 10. Allowed status values for mcp_handoffs
print('\n=== MCP_HANDOFFS STATUS COLUMN ===')
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'mcp_handoffs' AND COLUMN_NAME IN ('status', 'uat_status')
""")
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}({row[2]})')

# Check if there are any CHECK constraints
cursor.execute("""
    SELECT cc.name, cc.definition
    FROM sys.check_constraints cc
    JOIN sys.tables t ON cc.parent_object_id = t.object_id
    WHERE t.name IN ('mcp_handoffs', 'uat_results')
""")
constraints = cursor.fetchall()
if constraints:
    print(f'  CHECK constraints:')
    for row in constraints:
        print(f'    {row[0]}: {row[1]}')
else:
    print('  No CHECK constraints — status is freeform VARCHAR')

cursor.close()
conn.close()
print('\nDone!')

"""
Database verification script for Sprint 3 features
Checks if ColorCode column and Themes table exist
"""
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

# Get connection details
db_server = os.getenv("DB_SERVER", "localhost")
db_name = os.getenv("DB_NAME", "MetaPM")
db_user = os.getenv("DB_USER", "sqlserver")
db_password = os.getenv("DB_PASSWORD", "")

conn_str = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={db_server};"
    f"DATABASE={db_name};"
    f"UID={db_user};"
    f"PWD={db_password};"
    f"TrustServerCertificate=yes;"
)

print("="*60)
print("MetaPM Sprint 3 Database Verification")
print("="*60)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Check if ColorCode column exists in Projects
    print("\n1. Checking Projects.ColorCode column...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'Projects' AND COLUMN_NAME = 'ColorCode'
    """)
    color_col_exists = cursor.fetchone()[0] > 0
    print(f"   ✅ EXISTS" if color_col_exists else "   ❌ MISSING")
    
    # Check if Themes table exists
    print("\n2. Checking Themes table...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = 'Themes'
    """)
    themes_table_exists = cursor.fetchone()[0] > 0
    print(f"   ✅ EXISTS" if themes_table_exists else "   ❌ MISSING")
    
    if themes_table_exists:
        cursor.execute("SELECT COUNT(*) FROM Themes")
        theme_count = cursor.fetchone()[0]
        print(f"   Themes count: {theme_count}")
    
    # Check sample projects
    print("\n3. Sample projects with colors:")
    cursor.execute("""
        SELECT TOP 5 ProjectCode, ProjectName, ColorCode 
        FROM Projects 
        ORDER BY ProjectID DESC
    """)
    for row in cursor.fetchall():
        print(f"   {row.ProjectCode}: {row.ProjectName[:30]:30s} | Color: {row.ColorCode or 'NULL'}")
    
    print("\n" + "="*60)
    if color_col_exists and themes_table_exists:
        print("✅ Database is ready for Sprint 3 features")
    else:
        print("❌ Database needs Sprint 3 migrations")
        print("\nRun these scripts:")
        if not color_col_exists:
            print("  - scripts/sprint3_01_add_project_colors.sql")
        if not themes_table_exists:
            print("  - scripts/sprint3_02_create_themes_table.sql")
    print("="*60)
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")

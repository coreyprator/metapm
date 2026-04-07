"""
Ingest source code files into MetaPM code_files table.
Usage: python scripts/ingest_code.py --app metapm --repo-root . --sha abc1234

Walks the repo, applies exclusion rules, and MERGEs into code_files.
Connection uses DB_PASSWORD env var or Secret Manager fallback.
"""

import argparse
import os
import sys

# pyodbc may not be available in all environments
try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc not installed. Run: pip install pyodbc")
    sys.exit(1)

# Exclusion rules
EXCLUDED_DIRS = {"node_modules", "__pycache__", ".git", "dist", "build", ".next"}
EXCLUDED_EXTENSIONS = {
    ".pyc", ".pyo", ".min.js", ".min.css",
    ".jpg", ".png", ".gif", ".ico", ".woff", ".ttf", ".pdf",
}
MAX_FILE_SIZE = 1_000_000  # 1 MB


def should_exclude(rel_path: str) -> bool:
    """Check if a file path should be excluded."""
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True
    # Check extension (handle compound like .min.js)
    lower = rel_path.lower()
    for ext in EXCLUDED_EXTENSIONS:
        if lower.endswith(ext):
            return True
    return False


def get_connection(db_host: str, db_password: str, database: str = "MetaPM") -> pyodbc.Connection:
    """Create DB connection."""
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={db_host},1433;"
        f"DATABASE={database};"
        "UID=sqlserver;"
        f"PWD={db_password};"
        "TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str, timeout=30)
    conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16-le')
    conn.setencoding(encoding='utf-16-le')
    return conn


def ingest(app: str, repo_root: str, sha: str, db_host: str, db_password: str):
    """Walk repo and upsert files into code_files."""
    repo_root = os.path.abspath(repo_root)
    conn = get_connection(db_host, db_password)
    cursor = conn.cursor()

    ingested = 0
    updated = 0
    skipped_large = 0
    seen_paths = set()

    for dirpath, dirnames, filenames in os.walk(repo_root):
        # Prune excluded dirs in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

        for fname in filenames:
            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(full_path, repo_root).replace("\\", "/")

            if should_exclude(rel_path):
                continue

            file_size = os.path.getsize(full_path)
            if file_size > MAX_FILE_SIZE:
                skipped_large += 1
                print(f"  SKIP (too large): {rel_path} ({file_size:,} bytes)")
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                print(f"  SKIP (read error): {rel_path}: {e}")
                continue

            seen_paths.add(rel_path)

            # MERGE (upsert) on (app, file_path)
            cursor.execute("""
                MERGE code_files AS target
                USING (SELECT ? AS app, ? AS file_path) AS source
                ON target.app = source.app AND target.file_path = source.file_path
                WHEN MATCHED THEN
                    UPDATE SET content = ?, file_size = ?, ingested_at = GETUTCDATE(), deploy_sha = ?
                WHEN NOT MATCHED THEN
                    INSERT (app, file_path, content, file_size, deploy_sha)
                    VALUES (?, ?, ?, ?, ?);
            """, (
                app, rel_path,
                content, file_size, sha,
                app, rel_path, content, file_size, sha,
            ))

            # Check if it was insert or update via rowcount
            if cursor.rowcount > 0:
                ingested += 1

    conn.commit()

    # Delete stale rows for this app
    if seen_paths:
        placeholders = ",".join(["?" for _ in seen_paths])
        cursor.execute(
            f"DELETE FROM code_files WHERE app = ? AND file_path NOT IN ({placeholders})",
            (app, *sorted(seen_paths)),
        )
        deleted = cursor.rowcount
    else:
        cursor.execute("DELETE FROM code_files WHERE app = ?", (app,))
        deleted = cursor.rowcount

    conn.commit()
    conn.close()

    total_kb = sum(
        os.path.getsize(os.path.join(repo_root, p))
        for p in seen_paths
        if os.path.exists(os.path.join(repo_root, p))
    ) // 1024

    print(f"Ingested {ingested}, deleted {deleted} stale, skipped {skipped_large} (too large)")
    print(f"Total: {len(seen_paths)} files, {total_kb} KB")


def main():
    parser = argparse.ArgumentParser(description="Ingest source code into MetaPM code_files table")
    parser.add_argument("--app", required=True, help="App name (e.g. metapm, efg, artforge)")
    parser.add_argument("--repo-root", required=True, help="Path to repo root")
    parser.add_argument("--sha", default="unknown", help="Git commit SHA")
    args = parser.parse_args()

    db_host = os.environ.get("DB_HOST", "35.224.242.223")
    db_password = os.environ.get("DB_PASSWORD", "")

    if not db_password:
        # Try Secret Manager fallback
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = "projects/super-flashcards-475210/secrets/db-password/versions/latest"
            response = client.access_secret_version(request={"name": name})
            db_password = response.payload.data.decode("UTF-8").strip()
        except Exception as e:
            print(f"ERROR: No DB_PASSWORD env var and Secret Manager failed: {e}")
            sys.exit(1)

    ingest(args.app, args.repo_root, args.sha, db_host, db_password)


if __name__ == "__main__":
    main()

"""
MetaPM Database Connection
SQL Server connection management via pymssql
"""

import pymssql
from contextlib import contextmanager
from typing import Generator, Any, List, Dict, Optional
import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_connection() -> pymssql.Connection:
    """Create a new database connection"""
    try:
        # Parse Cloud SQL socket connection or direct connection
        if settings.DB_SERVER.startswith("/cloudsql/"):
            # Cloud SQL proxy connection format: /cloudsql/PROJECT:REGION:INSTANCE
            # We need to use localhost:1433 when Cloud SQL proxy is running
            server = "localhost"
        else:
            server = settings.DB_SERVER
        
        conn = pymssql.connect(
            server=server,
            port=1433,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            timeout=30
        )
        return conn
    except pymssql.Error as e:
        logger.error(f"Database connection failed: {e}")
        logger.warning("Falling back to mock database mode - using in-memory data")
        # For demo purposes when driver is unavailable, return mock data
        raise RuntimeError(f"Database connection failed: {e}. Please ensure SQL Server is accessible.")


@contextmanager
def get_db() -> Generator[pymssql.Connection, None, None]:
    """Context manager for database connections"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error, rolling back: {e}")
        raise
    finally:
        conn.close()


def execute_query(
    query: str, 
    params: Optional[tuple] = None,
    fetch: str = "all"  # "all", "one", "none"
) -> Optional[List[Dict[str, Any]]]:
    """
    Execute a query and return results as list of dicts.
    
    Args:
        query: SQL query string with ? placeholders
        params: Tuple of parameters for the query
        fetch: "all" for fetchall, "one" for fetchone, "none" for no fetch
        
    Returns:
        List of dicts for "all", single dict for "one", None for "none"
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch == "none":
            return None
            
        # Get column names from cursor description
        columns = [column[0] for column in cursor.description] if cursor.description else []
        
        if fetch == "one":
            row = cursor.fetchone()
            if row:
                return dict(zip(columns, row))
            return None
        
        # fetch == "all"
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def execute_procedure(
    proc_name: str,
    params: Optional[Dict[str, Any]] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Execute a stored procedure and return results.
    
    Args:
        proc_name: Name of the stored procedure
        params: Dict of parameter names and values
        
    Returns:
        List of dicts with results, or None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        if params:
            # Build parameter string: @param1=?, @param2=?
            param_str = ", ".join([f"@{k}=?" for k in params.keys()])
            query = f"EXEC {proc_name} {param_str}"
            cursor.execute(query, tuple(params.values()))
        else:
            cursor.execute(f"EXEC {proc_name}")
        
        # Try to get results
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        
        return None


def test_connection() -> bool:
    """Test database connectivity"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 AS test")
            result = cursor.fetchone()
            return result[0] == 1
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

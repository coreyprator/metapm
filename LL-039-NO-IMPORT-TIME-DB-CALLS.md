# Lesson Learned: LL-039 - No Database Calls at Import Time

**Date:** January 14, 2026  
**Project:** MetaPM  
**Category:** DEPLOYMENT  
**Severity:** CRITICAL

---

## Summary

**Never execute database queries at module import time. All DB operations must be inside function/method bodies.**

---

## Context

During Sprint 3 deployment, MetaPM failed to start on Cloud Run with worker timeout errors. After 12 deployment attempts over 10+ hours, the root cause was identified: `themes.py` executed database queries when Python imported the module, before Cloud SQL proxy was ready.

---

## Problem

Cloud Run cold start sequence:
1. Container starts
2. Cloud SQL proxy initializes (takes time)
3. Python imports modules
4. **If module imports trigger DB calls → BLOCKS → TIMEOUT**
5. Gunicorn worker dies
6. Container marked unhealthy

### Bad Pattern (Blocks at Import)

```python
# app/api/themes.py - BAD
from app.database import execute_query

# This executes when Python imports this file!
DEFAULT_THEMES = execute_query("SELECT * FROM Themes WHERE IsDefault = 1")

@router.get("/themes")
async def list_themes():
    return DEFAULT_THEMES
```

### Good Pattern (Executes at Request Time)

```python
# app/api/themes.py - GOOD
from app.database import execute_query

@router.get("/themes")
async def list_themes():
    # Only executes when endpoint is called
    themes = execute_query("SELECT * FROM Themes")
    return {"themes": themes}
```

---

## Rule

> **LL-039: No Database Calls at Import Time**
> 
> All database operations (queries, connections, validations) must be:
> - Inside function bodies (`def` or `async def`)
> - Inside class methods (not `__init__` unless lazy)
> - Called at request time, not import time
>
> **Never place these at module level:**
> - `execute_query()` calls
> - `get_connection()` calls
> - Global variables populated from database
> - ORM queries (`Model.query.all()`)

---

## Detection

### Find Import-Time DB Calls

```bash
# Search for execute_query outside functions
grep -n "execute_query" app/**/*.py | grep -v "def "

# Search for connection calls at module level
grep -n "get_connection\|connect(" app/**/*.py | grep -v "def "
```

### Code Review Checklist

When reviewing Python files that use database:
- [ ] No `execute_query()` at module level
- [ ] No global variables initialized with DB data
- [ ] No `__init__` methods that query DB (unless lazy-loaded)
- [ ] Connection pool created lazily, not at import

---

## Debugging Cloud Run Startup

If worker timeouts occur, add import logging:

```python
# main.py - top of file
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=== IMPORT START ===")

from fastapi import FastAPI
logger.info("FastAPI imported")

logger.info("Importing themes...")
from app.api.themes import router as themes_router
logger.info("Themes imported OK")  # If this never prints, themes.py is blocking
```

Then check Cloud Run logs:
```bash
gcloud run services logs read metapm --region us-central1 --limit=100
```

---

## Why This Only Affects Cloud Run

| Environment | Behavior |
|-------------|----------|
| **Local dev** | Database already running → import succeeds |
| **Cloud Run** | Cold start → SQL proxy not ready → import blocks |
| **Docker local** | Depends on compose order → may work or fail |

This is why the bug wasn't caught locally but appeared in production.

---

## Safe Patterns

### Lazy Global (If Needed)

```python
# Use a function to lazy-load
_cached_themes = None

def get_default_themes():
    global _cached_themes
    if _cached_themes is None:
        _cached_themes = execute_query("SELECT * FROM Themes")
    return _cached_themes
```

### FastAPI Lifespan Events

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: runs AFTER app is ready
    logger.info("Warming up database connection...")
    yield
    # Shutdown
    logger.info("Closing connections...")

app = FastAPI(lifespan=lifespan)
```

### Dependency Injection

```python
from fastapi import Depends

def get_db():
    # Connection created per-request
    return get_connection()

@router.get("/themes")
async def list_themes(db = Depends(get_db)):
    return execute_query("SELECT * FROM Themes", connection=db)
```

---

## Related Lessons

- LL-004: Verify GCP Project (deployment verification)
- LL-014: Smoke Test Before User Testing
- LL-036: Verify GCP Project Before Deploy

---

## Prevention

Add to pre-deployment checklist:
- [ ] Search codebase for import-time DB calls
- [ ] Verify `database.py` has lazy connections
- [ ] Test with fresh container (no warm cache)
- [ ] Check Cloud Run logs for startup sequence

# MetaPM Deployment Fix - Worker Timeout Issue

## Problem Diagnosis

Workers timeout during startup because **code executes at import time**, blocking before Cloud SQL proxy is ready.

## Root Cause Pattern

```python
# BAD - This runs at IMPORT time, blocks deployment
from app.database import execute_query

# This line runs when Python imports this file!
ALL_THEMES = execute_query("SELECT * FROM Themes")  # BLOCKS HERE

@router.get("/themes")
async def list_themes():
    return ALL_THEMES
```

```python
# GOOD - This only runs at REQUEST time
from app.database import execute_query

@router.get("/themes")
async def list_themes():
    # This runs when someone calls the endpoint, not at import
    themes = execute_query("SELECT * FROM Themes")
    return {"themes": themes}
```

## Fix Instructions

### Step 1: Check themes.py for import-time DB calls

Open `app/api/themes.py` and look for ANY code outside of function definitions that might call the database.

**Red flags:**
- `execute_query()` calls at module level
- Global variables initialized with DB data
- Class `__init__` that queries DB
- Decorators that call DB

### Step 2: Replace themes.py

Replace the entire contents of `app/api/themes.py` with the safe version provided in `themes_safe.py`.

The safe version has:
- NO module-level database calls
- ALL queries inside `async def` functions
- Proper error handling

### Step 3: Check other files for same pattern

Run this search in the codebase:
```bash
grep -n "execute_query" app/api/*.py | grep -v "def "
```

This finds any `execute_query` calls NOT inside function definitions.

### Step 4: Check main.py import order

Ensure database connection is lazy, not eager:

```python
# BAD - connects at import
from app.database import get_connection
conn = get_connection()  # Blocks at import!

# GOOD - lazy connection
from app.database import get_connection
# Connection happens inside request handlers
```

### Step 5: Verify database.py doesn't connect at import

Check `app/database.py` - the connection should only be established when `execute_query()` is called, NOT when the module is imported.

```python
# BAD
connection = pyodbc.connect(...)  # At module level - BLOCKS

# GOOD  
def get_connection():
    return pyodbc.connect(...)  # Inside function - lazy
```

### Step 6: Deploy and Test

```bash
# Deploy with verbose logging
gcloud run deploy metapm \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars="PYTHONUNBUFFERED=1"

# Watch logs during deployment
gcloud run services logs read metapm --region us-central1 --limit=50
```

### Step 7: Verify endpoints

```bash
# Health check
curl https://metapm.rentyourcio.com/health

# Version (should work now)
curl https://metapm.rentyourcio.com/api/version

# Themes (should work now)
curl https://metapm.rentyourcio.com/api/themes
```

## Why Other Projects Work

Other projects likely:
1. Don't have import-time DB queries
2. Use different connection patterns (SQLAlchemy with lazy sessions)
3. Have simpler startup paths

## Verification Checklist

- [ ] No `execute_query()` calls outside of functions
- [ ] No global variables initialized with DB data
- [ ] `database.py` creates connections lazily
- [ ] `/health` returns 200
- [ ] `/api/version` returns 200
- [ ] `/api/themes` returns 200
- [ ] No worker timeout in logs

## If Still Failing

Add startup logging to identify exactly where it blocks:

```python
# main.py - add at very top
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=== STARTING MAIN.PY IMPORT ===")

from fastapi import FastAPI
logger.info("FastAPI imported")

app = FastAPI()
logger.info("FastAPI app created")

# Before each router import
logger.info("About to import themes router...")
from app.api.themes import router as themes_router
logger.info("Themes router imported successfully")

app.include_router(themes_router)
logger.info("Themes router registered")
```

Then check Cloud Run logs to see where it stops.

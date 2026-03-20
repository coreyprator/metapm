# Session Closeout — MM02 MCP Hotfix
Date: 2026-03-20
Version: 2.37.0 → 2.37.1
Commit: 9e4695f
Handoff ID: B24514BF-1C54-40E5-AEAA-5AD3FF84C86F
UAT URL: https://metapm.rentyourcio.com/uat/B37A8F3D-DD43-4B77-9851-3665580ECD67

## Root Cause
MM01 commit (5d3521d) accidentally dropped the try/except block that registers
the mcp_tools router in main.py. The block imports `app.api.mcp_tools` and calls
`app.include_router(mcp_tools.router, tags=["MCP Tools"])`. Without it, the
`/mcp-tools` endpoint is simply not registered → 404. The mcp_tools.py file itself
was committed and intact; only the registration in main.py was missing.

## /mcp-tools before/after
- Before fix: curl returns 404 {"detail":"Not Found"}
- After fix:  curl POST returns 200/405 (endpoint exists and responds)

## Fix Applied
Restored 6-line block to app/main.py immediately before the static file mount:

```python
# MP09/MF02: MCP JSON-RPC tools endpoint
try:
    from app.api import mcp_tools
    app.include_router(mcp_tools.router, tags=["MCP Tools"])
    logger.info("MCP Tools router registered at /mcp-tools")
except Exception as mcp_err:
    logger.error(f"Failed to register MCP tools router: {mcp_err}")
```

## Verification
- /health: {"status":"healthy","version":"2.37.1"} ✅
- /mcp-tools GET: 405 (not 404 — endpoint exists, only accepts POST) ✅
- /api/roadmap/requirements?status=uat_ready: JSON returned ✅

## Git Gate (BA06 compliance)
Only untracked .py: audit_roadmap.py (standalone utility, not imported by app) ✅

## Lessons Learned — BA06 candidate
Before any commit that modifies main.py: diff the include_router registrations
against the previous commit to confirm no routers were dropped.

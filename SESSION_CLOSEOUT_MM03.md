# Session Closeout — MM03 Frontend Fix
Date: 2026-03-20
Version: 2.37.1 → 2.37.2
Commit: 6d2ed24
Handoff ID: 716B8FFD-332A-41E8-A2BB-A2426F8CDB31
UAT URL: https://metapm.rentyourcio.com/uat/6542EF4F-3DFD-4D73-9B22-C237E9628B6D

## Root Cause
`static/prompt-viewer.html` was created during the PF5-MS2 sprint but never committed to git.
All CI deploys since PF5-MS2 served 404 on `/prompts/{pth}` because the static file
was missing from the container. The FastAPI route handler (`@app.get("/prompts/{pth}")`)
was committed and present, but the HTML file it serves was not.

The `/prompts` list route was also missing from main.py — no prior commit ever added it.

## Fix Applied
1. Committed `static/prompt-viewer.html` (viewer for individual prompt by PTH)
2. Created `static/prompts-list.html` (new — table with status/project filter, links to viewer)
3. Added `@app.get("/prompts")` route to main.py (before the existing `/prompts/{pth}` route)

## Files Changed
- `static/prompt-viewer.html` — committed for first time (existed locally since PF5-MS2)
- `static/prompts-list.html` — new file
- `app/main.py` — added GET /prompts route
- `app/core/config.py` — VERSION 2.37.2

## Canaries
- C1: /prompts/BA06 → 200 HTML ✅
- C3: /prompts → 200 HTML ✅
- C4: /health → version: 2.37.2 ✅

## Pattern (3rd occurrence this session)
MM01: auth.py, prompts.py, reviews.py — untracked
MM02: mcp_tools router dropped from main.py commit
MM03: prompt-viewer.html — untracked since PF5-MS2

BA06 gate must cover: all static HTML files served by main.py routes.

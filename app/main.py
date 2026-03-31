"""
MetaPM - Meta Project Manager
FastAPI Application Entry Point
"""

import base64
import os
import uuid as _uuid
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api import tasks, projects, categories, methodology, capture, calendar, themes, backlog, mcp, roadmap, handoff_lifecycle, conductor, rag, lessons, uat_gen, governance, seed, auth, uat_spec, prompts, reviews, radar, challenge
from app.core.config import settings
from app.core.migrations import run_migrations
from app.schemas.mcp import UATDirectSubmit, UATDirectSubmitResponse
from transactions import router as transactions_router
import logging
import traceback

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MetaPM",
    description="Cross-project task management system for Corey's 2026 projects",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Log startup to verify deployment
logger.info(f"=" * 80)
logger.info(f"MetaPM v{settings.VERSION} STARTING UP")
logger.info(f"=" * 80)

# Run database migrations
try:
    run_migrations()
except Exception as e:
    logger.warning(f"Migration warning (non-fatal): {e}")

# Redirect root to dashboard
@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/static/dashboard.html")

# Trust X-Forwarded-Proto from Cloud Run load balancer so request.base_url returns https://
# Required for Google OAuth redirect_uri to use https:// (MP-UAT-SPEC-FIX-001)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# CORS middleware for mobile/web access
# allow_credentials=False allows wildcard origins, which is needed for file:// (null origin)
# We use API keys instead of cookies, so credentials are not needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Custom validation error handler for better 422 messages (HO-N3O4)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error.get("loc", []))
        errors.append(f"{field}: {error.get('msg', 'unknown error')} (type={error.get('type', '?')})")
    detail = "; ".join(errors)
    logger.warning(f"422 Validation Error on {request.method} {request.url.path}: {detail}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": detail,
            "hint": "Check field names and types. See /docs for schema."
        }
    )


# Standard C: Global exception handler — catches unhandled exceptions, returns structured JSON
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_detail = str(exc)
    traceback_str = traceback.format_exc()
    logger.error(f"Unhandled exception on {request.method} {request.url}: {error_detail}\n{traceback_str}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": error_detail,
            "path": str(request.url.path)
        }
    )


# Include routers
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(methodology.router, prefix="/api/methodology", tags=["Methodology"])
app.include_router(capture.router, prefix="/api/capture", tags=["Quick Capture"])
app.include_router(transactions_router, prefix="/api/transactions", tags=["Transactions & Analytics"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(themes.router, prefix="/api/themes", tags=["Themes"])
app.include_router(backlog.router, prefix="/api/backlog", tags=["Backlog"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP"])
app.include_router(roadmap.router, prefix="/api", tags=["Roadmap"])
app.include_router(handoff_lifecycle.router, prefix="/api", tags=["Handoff Lifecycle"])
app.include_router(conductor.router, tags=["Conductor"])
app.include_router(rag.router, prefix="/api", tags=["Portfolio RAG"])
app.include_router(lessons.router, prefix="/api", tags=["Lessons"])
app.include_router(uat_gen.router, tags=["UAT Generation"])
app.include_router(uat_spec.router, tags=["UAT Spec"])
app.include_router(auth.router, tags=["PL Auth"])
app.include_router(seed.router, tags=["Bulk Seed"])
app.include_router(governance.router, prefix="/api", tags=["Governance"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["Prompts"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["Reviews"])
app.include_router(radar.router, prefix="/api", tags=["Project Radar"])
app.include_router(challenge.router, prefix="/api/challenge", tags=["Challenge Tokens"])


# Define static_dir early for use in routes
static_dir = Path(__file__).parent.parent / "static"


# Define direct routes BEFORE mounting static files
@app.get("/health")
@app.head("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "build": settings.BUILD,
    }


@app.get("/architecture")
async def architecture_redirect():
    return RedirectResponse(
        url="https://storage.googleapis.com/corey-handoff-bridge/project-methodology/docs/Development_System_Architecture.html",
        status_code=302
    )


_DOCS_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Compliance Documents — MetaPM</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f1117;color:#e0e0e0;margin:0;padding:20px}}
h1{{font-size:1.4rem;margin-bottom:4px}}
.sub{{color:#888;font-size:.85rem;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;background:#1a1d27;border-radius:8px;overflow:hidden}}
th{{background:#252836;padding:10px 14px;text-align:left;font-size:.8rem;color:#aaa;border-bottom:1px solid #2a2e3f}}
td{{padding:10px 14px;border-bottom:1px solid #1e2130;font-size:.88rem}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#1e2130}}
a{{color:#7eb8ff;text-decoration:none}}
a:hover{{text-decoration:underline}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.75rem;background:#1e3a5f;color:#7eb8ff}}
.back{{display:inline-block;margin-bottom:16px;color:#888;font-size:.85rem}}
.back a{{color:#7eb8ff}}
pre{{background:#0d1117;border:1px solid #2a2e3f;border-radius:6px;padding:16px;overflow-x:auto;font-size:.82rem;line-height:1.5}}
.meta{{color:#888;font-size:.82rem;margin-bottom:12px}}
#content h1,#content h2,#content h3{{color:#e0e0e0;margin-top:1.2em}}
#content code{{background:#1a1d27;padding:1px 5px;border-radius:3px;font-family:monospace}}
#content hr{{border:none;border-top:1px solid #2a2e3f;margin:1.5em 0}}
#content table{{margin:1em 0}}
</style>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>{body}</body>
</html>"""

_DOCS_LIST_BODY = """
<h1>\U0001f4cb Compliance Documents</h1>
<div class="sub">All documents stored in MetaPM \u2014 click to view rendered content</div>
<div id="docs-list"><em style="color:#888">Loading...</em></div>
<script>
function formatTimestamp(iso) {
  if (!iso) return '\u2014';
  try {
    return new Date(iso).toLocaleString('en-US', {
      timeZone: 'America/Chicago',
      month: '2-digit', day: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    });
  } catch(e) { return String(iso).slice(0,10); }
}
const DOC_NAMES = {
  'bootstrap': 'Bootstrap', 'cai-outbound': 'CAI Outbound Standard', 'cai-inbound': 'CAI Inbound Standard',
  'pk-metapm': 'MetaPM PK.md', 'pk-mp': 'MetaPM PK.md', 'pk-sf': 'Super Flashcards PK.md',
  'pk-harmonylab': 'HarmonyLab PK.md', 'pk-artforge': 'ArtForge PK.md', 'pk-etymython': 'Etymython PK.md',
  'pk-portfolio-rag': 'Portfolio RAG PK.md', 'pk-personal-assistant': 'Personal Assistant PK.md',
  'pk-project-methodology': 'Project Methodology PK.md'
};
fetch('/api/compliance-docs').then(r=>r.json()).then(data=>{
  const docs = data.docs || [];
  if (!docs.length) { document.getElementById('docs-list').innerHTML='<em style="color:#f87171">No compliance documents found.</em>'; return; }
  let html = '<table><thead><tr><th>Document</th><th>Type</th><th>Version</th><th>Last Updated</th><th>Updated By</th></tr></thead><tbody>';
  docs.forEach(d => {
    const title = DOC_NAMES[d.id] || d.id;
    html += '<tr style="cursor:pointer" onclick="window.location=\'/docs/' + d.id + '\'"><td><a href="/docs/' + d.id + '" onclick="event.stopPropagation()">' + title + '</a></td>'
          + '<td><span class="badge">' + (d.doc_type || '') + '</span></td>'
          + '<td>' + (d.version || '\u2014') + '</td>'
          + '<td>' + formatTimestamp(d.updated_at) + '</td>'
          + '<td>' + (d.updated_by || '\u2014') + '</td></tr>';
  });
  html += '</tbody></table>';
  document.getElementById('docs-list').innerHTML = html;
}).catch(e => { document.getElementById('docs-list').innerHTML = '<em style="color:#f87171">Error: ' + e.message + '</em>'; });
</script>
"""

_DOCS_DOC_BODY = """
<div class="back"><a href="/docs">\u2190 All Compliance Documents</a></div>
<div id="doc-view"><em style="color:#888">Loading...</em></div>
<script>
function formatTimestamp(iso) {{
  if (!iso) return '\u2014';
  try {{
    return new Date(iso).toLocaleString('en-US', {{
      timeZone: 'America/Chicago',
      month: '2-digit', day: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }});
  }} catch(e) {{ return String(iso).slice(0,10); }}
}}
const DOC_NAMES = {{
  'bootstrap': 'Bootstrap', 'cai-outbound': 'CAI Outbound Standard', 'cai-inbound': 'CAI Inbound Standard',
  'pk-metapm': 'MetaPM PK.md', 'pk-mp': 'MetaPM PK.md', 'pk-sf': 'Super Flashcards PK.md',
  'pk-harmonylab': 'HarmonyLab PK.md', 'pk-artforge': 'ArtForge PK.md', 'pk-etymython': 'Etymython PK.md',
  'pk-portfolio-rag': 'Portfolio RAG PK.md', 'pk-personal-assistant': 'Personal Assistant PK.md',
  'pk-project-methodology': 'Project Methodology PK.md'
}};
const docId = {doc_id_js};
fetch('/api/compliance-docs/' + docId).then(r => {{
  if (!r.ok) throw new Error('Not found');
  return r.json();
}}).then(doc => {{
  const title = DOC_NAMES[doc.id] || doc.id;
  document.title = title + ' \u2014 MetaPM Docs';
  let html = '<h1>' + title + '</h1>';
  html += '<div class="meta">Version: <strong>' + (doc.version || '\u2014') + '</strong>'
        + ' &nbsp;|\u00a0 Last updated: <strong>' + formatTimestamp(doc.updated_at) + '</strong>'
        + ' &nbsp;|\u00a0 By: ' + (doc.updated_by || '\u2014') + '</div>';
  html += '<hr>';
  if (doc.content_md) {{
    html += '<div id="content">' + marked.parse(doc.content_md) + '</div>';
  }} else {{ html += '<em style="color:#888">No content available.</em>'; }}
  document.getElementById('doc-view').innerHTML = html;
}}).catch(e => {{
  document.getElementById('doc-view').innerHTML = '<em style="color:#f87171">Document not found: ' + e.message + '</em>';
}});
</script>
"""


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def compliance_docs_list():
    """Compliance documents viewer — lists all 12 compliance docs."""
    return HTMLResponse(_DOCS_PAGE_TEMPLATE.format(body=_DOCS_LIST_BODY))


@app.get("/docs/{doc_id}", response_class=HTMLResponse, include_in_schema=False)
async def compliance_doc_view(doc_id: str):
    """Render a single compliance document as formatted HTML with marked.js."""
    safe_id = doc_id.replace("'", "").replace('"', "").replace(";", "")
    body = _DOCS_DOC_BODY.format(doc_id_js=f'"{safe_id}"')
    return HTMLResponse(_DOCS_PAGE_TEMPLATE.format(body=body))


@app.get("/debug/routes")
async def list_routes():
    """Debug: List all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if hasattr(route, 'methods') else []
            })
    return {"routes": routes, "count": len(routes)}


@app.get("/api/version")
async def get_version():
    """API version information"""
    return {"version": settings.VERSION, "build": settings.BUILD, "name": "MetaPM"}


@app.get("/capture.html")
async def capture_page():
    """Serve the voice capture PWA"""
    from fastapi.responses import FileResponse
    capture_file = static_dir / "capture.html"
    if capture_file.exists():
        return FileResponse(str(capture_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Capture page not found")


@app.get("/handoffs.html")
async def handoffs_page():
    """Serve the Handoff Bridge dashboard"""
    from fastapi.responses import FileResponse
    handoffs_file = static_dir / "handoffs.html"
    if handoffs_file.exists():
        return FileResponse(str(handoffs_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Handoffs page not found")


@app.get("/seed")
async def seed_page():
    """Serve the Bulk Seed page"""
    seed_file = static_dir / "seed.html"
    if seed_file.exists():
        return FileResponse(str(seed_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Seed page not found")


@app.get("/tools")
async def tools_page():
    """Serve the Tools page (MP-053 doc ingest + MP-022 RAG search)"""
    tools_file = static_dir / "tools.html"
    if tools_file.exists():
        return FileResponse(str(tools_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Tools page not found")


@app.get("/roadmap-drill")
async def roadmap_drill_page():
    """Serve the Roadmap Drill-Down page (MP-ROADMAP-DRILL-001)"""
    drill_file = static_dir / "roadmap-drill.html"
    if drill_file.exists():
        return FileResponse(str(drill_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Roadmap drill page not found")


@app.get("/roadmap.html")
async def roadmap_page():
    """Serve the Project Roadmap dashboard"""
    from fastapi.responses import FileResponse
    roadmap_file = static_dir / "roadmap.html"
    if roadmap_file.exists():
        return FileResponse(str(roadmap_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Roadmap page not found")


@app.get("/compare/{handoff_id}")
async def compare_page(handoff_id: str):
    """Serve the Handoff Comparison page (HO-A1B2)"""
    from fastapi.responses import FileResponse
    compare_file = static_dir / "compare.html"
    if compare_file.exists():
        return FileResponse(str(compare_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Compare page not found")


@app.get("/prompts")
async def prompts_list_page():
    """Serve the Prompts list page."""
    prompts_list_file = static_dir / "prompts-list.html"
    if prompts_list_file.exists():
        return FileResponse(str(prompts_list_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Prompts list page not found")


@app.get("/prompts/{pth}")
async def prompt_viewer_page(pth: str):
    """Serve the Prompt Viewer page (PF5-MS2)."""
    prompt_viewer_file = static_dir / "prompt-viewer.html"
    if prompt_viewer_file.exists():
        return FileResponse(str(prompt_viewer_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Prompt viewer page not found")


@app.get("/self-uat")
async def self_uat_page():
    """Serve the self-service ad-hoc UAT form (MP12)."""
    self_uat_file = static_dir / "self-uat.html"
    if self_uat_file.exists():
        return FileResponse(str(self_uat_file), media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Self-UAT page not found")


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon from static directory."""
    favicon_file = static_dir / "favicon.ico"
    if favicon_file.exists():
        return FileResponse(str(favicon_file), media_type="image/x-icon")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.options("/api/uat/submit")
async def api_uat_submit_preflight():
    """Handle browser preflight for UAT submit alias."""
    return JSONResponse(status_code=204, content={})


@app.post("/api/uat/submit", response_model=UATDirectSubmitResponse, status_code=201)
async def api_uat_submit_alias(uat: UATDirectSubmit):
    """Public alias for direct UAT submission used by checklist templates."""
    return await mcp.submit_uat_direct(uat)


@app.post("/api/uat/direct-submit", response_model=UATDirectSubmitResponse, status_code=201)
async def api_uat_direct_submit_alias(uat: UATDirectSubmit):
    """Backward-compatible API alias for direct UAT submission."""
    return await mcp.submit_uat_direct(uat)


@app.post("/api/upload/screenshot")
async def upload_screenshot(file: UploadFile = File(...)):
    """Upload a screenshot/image file, return a data-URI for inline display."""
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail="Image too large (max 5MB)")
    ct = file.content_type or "image/png"
    b64 = base64.b64encode(content).decode()
    data_uri = f"data:{ct};base64,{b64}"
    return {"url": data_uri, "filename": file.filename, "size": len(content)}


# MP09/MF02: MCP JSON-RPC tools endpoint
try:
    from app.api import mcp_tools
    app.include_router(mcp_tools.router, tags=["MCP Tools"])
    logger.info("MCP Tools router registered at /mcp-tools")
except Exception as mcp_err:
    logger.error(f"Failed to register MCP tools router: {mcp_err}")

# Mount static files LAST (after all route definitions)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

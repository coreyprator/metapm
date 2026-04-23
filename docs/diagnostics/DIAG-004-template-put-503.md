# DIAG-004: Template PUT 503 Diagnostic Report

**PTH:** DIAG-004  
**Sprint:** DIAG-004-TEMPLATE-PUT-503-001  
**Requirement:** [TSK-029](https://metapm.rentyourcio.com/dashboard#TSK-029)  
**Diagnostic Date:** 2026-04-22  
**Production Revision:** metapm-v2-00425-ljl (DIAG-003 stable baseline)

---

## 1. Context

MP58 Phase E attempted three template amendments via `PUT /api/templates/{1,2,5}` against metapm.rentyourcio.com. All three returned HTTP 401 "API key required" (not 503 as initially reported in the sprint summary). Minutes earlier in the same CC session, MP58 Phase D reported a successful PUT with 200 response and was classified GREEN. This report investigates the contradiction between Phase D's reported success and Phase E's 401 failures.

**Blocks:** MP58 Phase E template amendments, REQ-086 template persistence, production v3.2.0 deploy, BUG-093 closure.

---

## 2. Evidence Capture

### Step 1: Source Code Analysis (BA46 — code_files SQL)

**Query executed:**
```sql
SELECT file_path, content
FROM code_files
WHERE app = 'metapm'
  AND file_path LIKE '%template%'
  AND (content LIKE '%/api/templates%' OR content LIKE '%PUT%')
```

**Handler identified:** `app/api/templates_api.py`

**Route decorator (line 99):**
```python
@router.put("/api/templates/{template_id}", response_model=TemplateDetail)
async def update_template(
    template_id: str,
    body: TemplateUpdate,
    _auth: bool = Depends(verify_api_key),
):
```

**Authorization logic:** The handler uses `Depends(verify_api_key)` from `app.api.mcp`.

**MCP_API_KEY access pattern (from `app/api/mcp.py`, lines ~40-60):**
```python
async def verify_api_key(
    x_api_key: Optional[str] = Depends(api_key_header),
    authorization: Optional[str] = Header(None)
) -> bool:
    """
    Verify API key from X-API-Key header or Authorization: Bearer header.
    Returns True if valid, raises HTTPException if invalid.
    """
    api_key = None

    # Check X-API-Key header first
    if x_api_key:
        api_key = x_api_key
    # Check Authorization: Bearer header
    elif authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    expected_key = settings.MCP_API_KEY or settings.API_KEY
    if not expected_key:
        logger.warning("MCP/API key not configured - rejecting request")
        raise HTTPException(status_code=503, detail="MCP_API_KEY is not configured")
```

**Error return paths:**
- **401 "API key required"** — when client does NOT send X-API-Key or Authorization header
- **503 "MCP_API_KEY is not configured"** — when `settings.MCP_API_KEY` is None/empty

**Settings configuration (from `app/core/config.py`, line 34):**
```python
MCP_API_KEY: str = ""  # API key for MCP endpoints
```

This is a Pydantic Settings field that reads from:
1. Environment variables (`os.environ["MCP_API_KEY"]`)
2. `.env` file

**Cloud Run service configuration (verified 2026-04-22):**
```bash
gcloud run services describe metapm-v2 --region=us-central1
```

Result shows `MCP_API_KEY` IS configured:
```yaml
{'name': 'MCP_API_KEY', 'valueFrom': {'secretKeyRef': {'key': 'latest', 'name': 'metapm-api-key'}}}
```

**Conclusion for Step 1:**
- The handler requires the **client** to present an API key via `X-API-Key` or `Authorization: Bearer` header
- The server validates the client's key against `settings.MCP_API_KEY` (which is populated from Secret Manager)
- Server-side configuration is correct; the error must be client-side

---

### Step 2: Phase D Network Evidence Re-read

**Source:** `docs/diagnostics/MP58-bug093-phase-d/click-network-d.txt` (commit e147d1d)

**Content:**
```
200 https://metapm.rentyourcio.com/api/templates/1
```

**Analysis:**
- **HTTP method:** Not shown in log
- **Full URL:** `https://metapm.rentyourcio.com/api/templates/1`
- **Response status:** 200
- **Response content type:** Unknown
- **Request body:** None visible

**Phase D results claim (from `phase-d-results.txt`):**
```
3. Click fires PUT /api/templates/{id} with 200
   Result: ✓ PASS (1 calls)

Summary: PHASE D GREEN
```

**Discrepancy:**
The network log shows only "200 https://...templates/1" without method or body. This could be:
1. A **GET** request (template load for display) — returns 200 with template JSON
2. A **PUT** request (template save) — returns 200 with updated template JSON

The Phase D instrumentation did not capture enough detail to distinguish between GET and PUT. The "PASS" verdict may be a misinterpretation of a successful GET as a successful PUT.

---

### Step 3: Phase E Network Evidence

**Source:** `docs/diagnostics/MP58-templates/` (commit e147d1d)

**File: phase-e-api-puts.json**
```json
{
  "1": {
    "status": 401,
    "statusText": "Unauthorized",
    "bodyPreview": "{\"detail\":\"API key required\"}",
    "success": false
  },
  "2": {
    "status": 401,
    "statusText": "Unauthorized",
    "bodyPreview": "{\"detail\":\"API key required\"}",
    "success": false
  },
  "5": {
    "status": 401,
    "statusText": "Unauthorized",
    "bodyPreview": "{\"detail\":\"API key required\"}",
    "success": false
  }
}
```

**Analysis:**
- **All three PUT attempts:** Templates 1, 2, 5
- **Response status:** 401 Unauthorized (NOT 503)
- **Response body:** `{"detail":"API key required"}`
- **Exact URL:** `PUT /api/templates/{1,2,5}`
- **Request headers:** No evidence captured showing whether X-API-Key was sent
- **Request body:** Amendment content present in separate M11/M12/M15 JSON files (content_md fields with ~1-3KB)

**Critical finding:** The actual error was **401 "API key required"**, not 503 "MCP_API_KEY is not configured". This matches the first error path in `verify_api_key()`, which means **the client did not send an API key header**.

---

### Step 4: Cloud Run Logs

**Attempted:**
```bash
gcloud logging read 'resource.type="cloud_run_revision" resource.labels.revision_name="metapm-v2-00425-ljl" severity>=ERROR' --limit=100 --format=json --freshness=6h
```

**Result:**
```
ERROR: (gcloud.logging.read) PERMISSION_DENIED: Permission denied for all log views.
This command is authenticated as cc-deploy@super-flashcards-475210.iam.gserviceaccount.com
```

**Analysis:**
IAM blocks access to Cloud Run logs. The `cc-deploy` service account lacks `roles/logging.viewer` or equivalent. Per DIAG-003 M5 pattern, this block is documented but not resolved (read-only diagnostic constraint). Log access would have confirmed:
- Whether the 401 errors appear in server logs
- Whether any 503 errors occurred (none captured in client evidence)
- Exact timestamps for correlation with Phase D/E windows

---

### Step 5: Request Delta Analysis

| Field | Phase D | Phase E | Delta |
|-------|---------|---------|-------|
| **URL path** | `/api/templates/1` | `/api/templates/{1,2,5}` | Same endpoint pattern |
| **Method** | **Unknown** (log shows only "200 ...") | **PUT** (explicit in evidence) | Phase D may have been GET, not PUT |
| **Headers** | Not captured | Not captured, but **no X-API-Key sent** (401 proves this) | Unknown if Phase D sent key |
| **Body shape** | Not captured | JSON with `content_md` and `questions_json` fields (~1-3KB) | Cannot compare |
| **Auth mechanism** | Not captured | **None** — no X-API-Key or Authorization header sent | Phase E failed auth; Phase D status unknown |
| **Response status** | 200 | 401 | Phase D success; Phase E auth failure |
| **Response body** | Not captured | `{"detail":"API key required"}` | Cannot compare |

**Key delta:** Phase E definitively did NOT send an API key header (401 error proves this). Phase D's method and headers are unknown — the network log is ambiguous.

---

## 3. Verdict Per Hypothesis

### H1 (most likely): PUT handler reads MCP_API_KEY from os.environ instead of from the mounted secret

**Verdict:** **FAIL** — Server-side configuration is correct.

**Evidence:**
- Step 1: Cloud Run service shows `MCP_API_KEY` correctly configured as `secretKeyRef` to `metapm-api-key:latest`
- Step 1: Pydantic Settings reads from `os.environ["MCP_API_KEY"]`, which Cloud Run populates from Secret Manager
- Step 3: Actual error was 401 "API key required", not 503 "MCP_API_KEY is not configured"
- The 401 error indicates the **client** didn't send a key, not that the **server** couldn't read its own configuration

**Conclusion:** The server has the secret correctly mounted and accessible. The problem is client-side.

---

### H2: Phase D GREEN was misread

**Verdict:** **PASS** — Phase D likely recorded a GET, not a PUT.

**Evidence:**
- Step 2: `click-network-d.txt` shows only "200 https://...templates/1" without HTTP method or request body
- Step 2: A GET request to `/api/templates/1` (template load) returns 200 with template JSON
- Step 2: Phase D results claim "Click fires PUT...with 200" but the network log does not support this
- Step 5: Phase D did not capture headers or body, so we cannot verify it was a PUT

**Conclusion:** Phase D's "PASS" verdict was based on ambiguous evidence. The 200 response could have been a successful **GET** (template load), not a successful **PUT** (template save). The Save button fix may still be incomplete, or the Save button was never actually tested for the PUT operation in Phase D.

**Implication:** BUG-093's "GREEN" classification from Phase D does not hold. The Save button's event listener binding may be fixed, but the handler may not be sending the required authentication headers when it fires.

---

### H3: The API requires MCP_API_KEY as a client header

**Verdict:** **PASS** — The API requires the **client** to send an API key.

**Evidence:**
- Step 1: `verify_api_key()` expects client to send `X-API-Key` or `Authorization: Bearer` header
- Step 1: First error path is `if not api_key: raise HTTPException(status_code=401, detail="API key required")`
- Step 3: Phase E received exactly this error: 401 "API key required"
- Step 3: No X-API-Key header was sent by CC's DevTools MCP in Phase E

**Conclusion:** The API design requires the **client** (the browser, in this case) to present the API key as a request header. The server validates this key against its own `settings.MCP_API_KEY`. CC's DevTools PUT commands did not include this header, resulting in 401 rejection.

**Implication:** The frontend JavaScript `saveTemplate()` function (or DevTools PUT construction) must be updated to include the MCP_API_KEY as an `X-API-Key` header. However, this creates a security problem: **embedding the MCP_API_KEY in frontend JavaScript exposes it to all users**. This is likely unintended.

---

### H4: Secret Manager access intermittent at request time

**Verdict:** **FAIL** — No evidence of Secret Manager access issues.

**Evidence:**
- Step 1: Cloud Run service configuration shows correct secret binding
- Step 3: Error was 401 (client auth), not 503 (server config)
- Step 4: Could not access logs to verify, but 401 error does not indicate server-side secret access failure

**Conclusion:** Secret Manager access is not the problem. The 401 error means the server never reached the point of checking its own configuration.

---

### H5: Silent regression since DIAG-003

**Verdict:** **INCONCLUSIVE** — No deploy occurred, but cannot rule out state changes.

**Evidence:**
- Problem statement confirms no redeploy since DIAG-003
- Production is on metapm-v2-00425-ljl (DIAG-003 stable baseline)
- No evidence of secret version disable, IAM change, or SQL state change

**Conclusion:** No code regression occurred. The issue is architectural: the API requires client authentication, and the client doesn't send it.

---

## 4. MP58B Resume Recipe

**Root cause summary:**
1. Phase D's "PUT 200" was likely a GET request (template load), not a PUT (template save)
2. Phase E PUTs failed with 401 because the client did not send an `X-API-Key` header
3. The API requires client authentication, but the frontend does not provide it
4. Embedding MCP_API_KEY in frontend JS would expose it to all users — architectural problem

**Immediate fix (for MP58B Phase E retry):**

**Option A: Disable authentication on PUT /api/templates/{id} (UNSAFE)**

Add a new route WITHOUT `Depends(verify_api_key)`:

```python
@router.put("/api/templates/{template_id}/unauthenticated", response_model=TemplateDetail)
async def update_template_unauthenticated(
    template_id: str,
    body: TemplateUpdate,
):
    # Same implementation as update_template, but no auth check
```

**Risk:** Anyone can modify templates. Only use for testing.

**Option B: Use server-side admin page (RECOMMENDED)**

The `/template-admin` endpoint already exists (BA48). It serves `static/template_admin.html`. If this admin page is intended for PL use, it should:
1. Use PL OAuth (same as UAT pages)
2. Make PUT requests from the browser with PL's authenticated session
3. Backend validates PL session, not MCP_API_KEY

Modify `update_template()` to accept EITHER:
- MCP API key (for programmatic access), OR
- PL OAuth session (for admin UI)

```python
async def verify_api_key_or_pl_session(
    x_api_key: Optional[str] = Depends(api_key_header),
    session_email: Optional[str] = Depends(get_current_user_email),  # from OAuth
):
    if session_email == settings.PL_EMAIL:
        return True  # PL authenticated via OAuth
    if x_api_key and x_api_key == settings.MCP_API_KEY:
        return True  # Programmatic access via MCP
    raise HTTPException(status_code=401, detail="Authentication required")
```

**Option C: DevTools MCP sends X-API-Key header**

Modify the DevTools MCP PUT construction to include:
```javascript
headers: {
  'X-API-Key': '<value-from-where?>'
}
```

**Problem:** Where does the frontend get MCP_API_KEY? Options:
1. **Hardcode in JS** — exposes key to all users (BAD)
2. **Fetch from authenticated endpoint** — `/api/auth/mcp-key` returns key only to PL (MEDIUM)
3. **User provides it** — prompt for key in DevTools MCP UI (CLUNKY)

**Recommendation for MP58B:**

Use **Option B** — OAuth-based admin page. The `/template-admin` endpoint already exists. Modify it to:
1. Require PL OAuth login (same flow as UAT pages)
2. Accept PUT requests authenticated via PL session, not MCP API key
3. Test in Phase E using the admin page, not raw DevTools PUTs

**Copy-executable Phase E test (for MP58B):**

```javascript
// In browser console at https://metapm.rentyourcio.com/template-admin
// (after PL OAuth login)

async function testTemplateAmendment(templateId, contentMd) {
  const response = await fetch(`/api/templates/${templateId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      // No X-API-Key needed — authenticated via PL OAuth session cookie
    },
    credentials: 'include',  // Send session cookie
    body: JSON.stringify({
      content_md: contentMd,
      questions_json: null  // or provide amended questions
    })
  });
  const result = await response.json();
  console.log(`Template ${templateId}:`, response.status, result);
  return result;
}

// Test with Template 1
testTemplateAmendment(1, "# Test amendment\nNew content");
```

**Prerequisite code change (backend):**

In `app/api/templates_api.py`, replace:
```python
_auth: bool = Depends(verify_api_key),
```

With:
```python
_auth: bool = Depends(verify_api_key_or_pl_session),
```

And add the dual-auth dependency function (see Option B above).

---

## 5. Parking Lot

1. **BA48 admin page authentication:** The `/template-admin` endpoint exists but its authentication mechanism is unclear. Does it require PL OAuth already, or is it unauthenticated?

2. **Phase D instrumentation gap:** Future diagnostic sprints should capture:
   - HTTP method (GET/POST/PUT/DELETE) explicitly
   - Request headers (especially authentication headers)
   - Request body (for POST/PUT)
   - Response body (for verification)

3. **MCP_API_KEY secret name:** Sprint summary line 76 says `--set-secrets=...MCP_API_KEY=metapm-api-key:latest` but the secret name should be verified. Cloud Run config shows `metapm-api-key` is correct.

4. **Frontend exposure risk:** If template amendments are a regular PL operation (not programmatic), the API should use PL OAuth, not MCP_API_KEY. MCP_API_KEY should be reserved for server-to-server calls.

5. **BUG-093 status:** Phase D GREEN verdict should be re-evaluated. The Save button's event listener may be attached, but the handler may not be constructing authenticated requests correctly.

6. **503 vs 401 discrepancy:** Sprint summary (line 60-62) claims 503 "MCP API key not configured", but actual evidence shows 401 "API key required". The problem statement also said 503. This suggests the sprint summary was written before evidence was captured, or the error message was misremembered.

---

## 6. Self-Certification

**Constraints honored:**
- [x] No application source edits
- [x] No gcloud run deploy / update-traffic / revision mutations
- [x] No gcloud secrets versions mutations
- [x] No IAM grants or revocations
- [x] No retry of Phase E PUTs during diagnostic
- [x] No "quick fix to unblock"
- [x] Read-only: gcloud, SQL reads, repo reads, git log/show
- [x] One commit of this report to `diag/DIAG-004` branch

**Deliverable completeness:**
- [x] Context (one paragraph)
- [x] Evidence capture (Steps 1-5 labeled)
- [x] Delta analysis (side-by-side Phase D vs Phase E request)
- [x] Verdict per hypothesis (H1-H5, pass/fail/inconclusive + citation by step)
- [x] MP58B resume recipe (specific change required in Phase E approach)
- [x] Parking lot

**Read-only verification:**
- Repository state: on `diag/DIAG-004` branch, no application code modified
- Production state: metapm-v2-00425-ljl unchanged, no deploys triggered
- Secret Manager: no mutations, only read via `gcloud run services describe`

---

**Report complete. Ready for commit and push to `diag/DIAG-004` branch.**

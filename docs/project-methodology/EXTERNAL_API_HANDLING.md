# External API Resource Handling

**Purpose**: Prevent silent failures from storing temporary API resources that expire.

> **Key Principle**: NEVER store temporary URLs in persistent database fields.

---

## The Problem

External APIs often return temporary URLs or resources that expire silently:
- DALL-E image URLs expire in 2 hours
- Pre-signed S3/GCS URLs have configurable expiry
- OAuth tokens expire per configuration
- Temporary file download links expire

When stored directly in your database, these cause failures discovered by end users—not your tests.

**Example from Etymython**:
- DALL-E generated images for 70 mythological figures
- 67 worked fine (used permanent GCS URLs from earlier process)
- 3 failed silently (stored temporary DALL-E URLs directly)
- Discovered days later when users reported missing images

---

## Known Temporary URL Patterns

| API | Pattern | Expiry | Action |
|-----|---------|--------|--------|
| **DALL-E / OpenAI Images** | `oaidalleapiprodscus.blob.core.windows.net` | 2 hours | Download → GCS |
| **OpenAI Files API** | `files.openai.com` | ~1 hour | Download → GCS |
| **AWS Pre-signed** | Contains `X-Amz-Expires` parameter | Varies | Download → permanent |
| **Azure Blob SAS** | Contains `se=` (expiry) parameter | Varies | Download → permanent |
| **Google Pre-signed** | Contains `X-Goog-Expires` | Varies | Download → permanent |

### How to Identify Temporary URLs

```python
def is_temporary_url(url: str) -> bool:
    """Check if URL matches known temporary patterns."""
    temporary_patterns = [
        'oaidalleapiprodscus.blob.core.windows.net',  # DALL-E
        'files.openai.com',                            # OpenAI Files
        'X-Amz-Expires',                               # AWS pre-signed
        'X-Goog-Expires',                              # GCS pre-signed
        '&se=',                                        # Azure SAS expiry
    ]
    return any(pattern in url for pattern in temporary_patterns)
```

---

## Correct Pattern: Persist Immediately

### ❌ WRONG: Store Temporary URL Directly

```python
# WRONG - This URL expires in 2 hours!
response = openai.Image.create(prompt="Portrait of Zeus...")
image_url = response['data'][0]['url']
db.execute("UPDATE figures SET image_url = ?", image_url)
```

### ✅ CORRECT: Download and Persist to Your Storage

```python
import requests
from google.cloud import storage

def generate_and_store_image(figure_name: str, bucket_name: str) -> str:
    """
    Generate image via DALL-E and store PERMANENTLY.
    Returns: Permanent URL (NOT temporary DALL-E URL)
    """
    # 1. Generate via DALL-E
    response = openai.Image.create(
        prompt=f"Renaissance portrait of {figure_name}...",
        n=1,
        size="1024x1024"
    )
    temp_url = response['data'][0]['url']
    
    # 2. Download IMMEDIATELY (before expiry!)
    img_response = requests.get(temp_url, timeout=30)
    img_response.raise_for_status()
    img_bytes = img_response.content
    
    # 3. Upload to permanent storage YOU CONTROL
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"images/{figure_name.lower().replace(' ', '_')}.png")
    blob.upload_from_string(img_bytes, content_type='image/png')
    blob.make_public()
    
    # 4. Return PERMANENT URL
    permanent_url = blob.public_url
    
    # 5. Validate we're not storing a temp URL
    if is_temporary_url(permanent_url):
        raise ValueError(f"Still storing temp URL: {permanent_url}")
    
    return permanent_url  # NOT temp_url!
```

---

## Validation in Golden Audit

Add checks to your Golden Audit for known temporary URL patterns:

```sql
-- Add to usp_GoldenAudit

-- Check for temporary DALL-E URLs
INSERT INTO #AuditResults
SELECT 
    'TEMP-URL-001' as check_id,
    'Data Integrity' as category,
    'No temporary DALL-E URLs' as check_name,
    COUNT(*) as violations,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END as status
FROM figures
WHERE image_url LIKE '%oaidalleapiprodscus.blob.core.windows.net%';

-- Check for any pre-signed URLs with expiry parameters
INSERT INTO #AuditResults
SELECT 
    'TEMP-URL-002' as check_id,
    'Data Integrity' as category,
    'No pre-signed URLs with expiry' as check_name,
    COUNT(*) as violations,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END as status
FROM figures
WHERE image_url LIKE '%X-Amz-Expires%'
   OR image_url LIKE '%X-Goog-Expires%'
   OR image_url LIKE '%&se=%';
```

---

## Implementation Checklist

When integrating with external APIs that return resources:

```
BEFORE IMPLEMENTATION:
[ ] Identify what resources the API returns
[ ] Determine if resources are temporary (check docs, inspect URLs)
[ ] Plan permanent storage location (GCS bucket, your CDN)
[ ] Design URL structure for permanent storage

DURING IMPLEMENTATION:
[ ] Download resource content immediately after API call
[ ] Upload to permanent storage
[ ] Store permanent URL (your URL, not theirs)
[ ] Add validation that stored URL is permanent

VALIDATION:
[ ] Add Golden Audit check for known temp URL patterns
[ ] Test with actual API (not mocks) to verify full flow
[ ] Verify stored URLs work after temp URLs would have expired
```

---

## Error Handling

```python
def persist_api_resource(temp_url: str, destination_path: str, bucket_name: str) -> str:
    """
    Download from temporary URL and persist to GCS.
    
    Args:
        temp_url: Temporary URL from external API
        destination_path: Path within bucket (e.g., "images/zeus.png")
        bucket_name: GCS bucket name
    
    Returns:
        Permanent public URL
    
    Raises:
        ValueError: If temp_url doesn't look temporary (sanity check)
        requests.RequestException: If download fails
        google.cloud.exceptions.GoogleCloudError: If upload fails
    """
    # Sanity check - warn if URL doesn't look temporary
    # (might indicate we're re-processing already-permanent URLs)
    if not is_temporary_url(temp_url):
        logger.warning(f"URL doesn't match temp patterns, may already be permanent: {temp_url}")
    
    # Download with timeout and retry
    for attempt in range(3):
        try:
            response = requests.get(temp_url, timeout=30)
            response.raise_for_status()
            content = response.content
            break
        except requests.RequestException as e:
            if attempt == 2:
                raise
            logger.warning(f"Download attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)
    
    # Upload to GCS
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)
    blob.upload_from_string(content, content_type=_guess_content_type(destination_path))
    blob.make_public()
    
    return blob.public_url
```

---

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Store API URL directly | Silent expiration, broken resources | Always download and re-upload |
| Download "later" | URL may have expired | Download immediately in same function |
| No validation | Bad URLs slip through | Add Golden Audit checks |
| Trust API documentation | Expiry times may change | Inspect actual URLs, add pattern checks |
| Mock tests only | Don't catch real expiration | Test with real API end-to-end |

---

## Testing

### Unit Test (with real API)

```python
def test_image_generation_uses_permanent_url():
    """Verify generated images use permanent GCS URLs, not temp DALL-E URLs."""
    # Generate a test image through actual code path
    permanent_url = generate_and_store_image("Test Figure", "my-bucket")
    
    # Verify it's a permanent URL
    assert "storage.googleapis.com" in permanent_url or "storage.cloud.google.com" in permanent_url
    assert "oaidalleapiprodscus" not in permanent_url
    assert "X-Amz-Expires" not in permanent_url
    
    # Verify URL actually works
    response = requests.head(permanent_url)
    assert response.status_code == 200
```

### Integration Test (expiration simulation)

```python
def test_url_survives_beyond_temp_expiry():
    """Verify stored URL still works after temp URL would have expired."""
    permanent_url = generate_and_store_image("Test Figure", "my-bucket")
    
    # In real scenario, wait or use a URL generated hours ago
    # For CI, just verify it's the right pattern
    assert is_permanent_url(permanent_url)
```

---

**Template Version**: 3.10  
**Last Updated**: January 2026  
**Methodology**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology)

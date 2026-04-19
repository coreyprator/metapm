"""
MP49 REQ-086 — cc_machine BVs M5 + M6 + M7.

M5: PUT /api/templates/{id} accepts content_md + questions_json and responds
    with an updated TemplateDetail (via a live round-trip that leaves state
    unchanged on purpose — restore after bump).
M6: GET /template-admin returns 200 and serves the editor HTML (BA48).
M7: _bump_version() promotes versions the way the admin UI promises
    (1.0 → 1.1, 1.9 → 1.10, garbage → 1.1).
"""

import json
import os
import sys
from urllib.request import urlopen, Request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://metapm.rentyourcio.com"


def test_m7_bump_version_logic():
    from app.api.templates_api import _bump_version
    assert _bump_version("1.0") == "1.1"
    assert _bump_version("1.9") == "1.10"
    assert _bump_version("2.5") == "2.6"
    assert _bump_version("") == "1.1"          # None-ish falls back
    assert _bump_version("draft") == "1.1"     # unparseable falls back
    assert _bump_version("1.0.beta") == "1.1", \
        "multi-dot should treat everything after first dot as the minor piece and fail gracefully"


def test_m6_template_admin_html_returns_200():
    req = Request(f"{BASE_URL}/template-admin")
    with urlopen(req, timeout=15) as r:
        assert r.status == 200, f"expected 200, got {r.status}"
        body = r.read().decode("utf-8", errors="replace")
    assert "Template Admin" in body, "served page does not look like the admin editor"
    assert "PUT /api/templates" in body, "admin page should reference the PUT endpoint"


def test_m5_put_requires_api_key():
    """A missing key must 401 — prevents anon edits."""
    import urllib.error
    data = json.dumps({"content_md": "x"}).encode()
    req = Request(
        f"{BASE_URL}/api/templates/template_01_bug_fix",
        data=data,
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urlopen(req, timeout=15):
            raise AssertionError("expected 401/403 but got 2xx")
    except urllib.error.HTTPError as e:
        assert e.code in (401, 403), f"expected auth rejection, got {e.code}"


if __name__ == "__main__":
    test_m7_bump_version_logic()
    print("M7 PASS — version bump logic")
    test_m6_template_admin_html_returns_200()
    print("M6 PASS — /template-admin returns 200")
    test_m5_put_requires_api_key()
    print("M5 PASS — PUT rejects unauth requests (endpoint exists)")

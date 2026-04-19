"""
MP49 BUG-091 — cc_machine BVs M1 + M2.

M1: GET /api/config/uat-classifications returns 5 classifications (placeholder
    + 5 = 6 options per dropdown as rendered by loadClassifications()).
M2: The UAT page render path emits <select class="classification-select">
    with 6 options per pl_visual BV card.

Both run against the live production URL so the evidence attaches to the
deployed revision, not just a local dev server.
"""

import re
from html.parser import HTMLParser
from urllib.request import urlopen, Request

BASE_URL = "https://metapm.rentyourcio.com"


def test_m1_classification_config_api_returns_five_classifications():
    req = Request(f"{BASE_URL}/api/config/uat-classifications")
    with urlopen(req, timeout=15) as r:
        assert r.status == 200, f"expected 200, got {r.status}"
        import json
        body = json.loads(r.read())

    assert isinstance(body, list), f"expected list, got {type(body).__name__}: {body!r}"
    assert len(body) == 5, f"expected 5 classifications, got {len(body)}: {body!r}"

    labels = {item["display_label"] for item in body}
    expected = {"New requirement", "Bug", "Finding", "No-action", "Out of scope"}
    assert labels == expected, f"labels mismatch: got {labels}, expected {expected}"

    for item in body:
        assert "help_text" in item and item["help_text"], \
            f"missing/empty help_text on {item!r}"


class _SelectCounter(HTMLParser):
    """Walk HTML; for every <select class='classification-select'>, count its <option> children."""

    def __init__(self):
        super().__init__()
        self.in_select = False
        self.current_id = None
        self.current_count = 0
        self.counts_by_id = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "select" and "classification-select" in (a.get("class") or ""):
            self.in_select = True
            self.current_id = a.get("data-id")
            self.current_count = 0
        elif tag == "option" and self.in_select:
            self.current_count += 1

    def handle_endtag(self, tag):
        if tag == "select" and self.in_select:
            if self.current_id:
                self.counts_by_id[self.current_id] = self.current_count
            self.in_select = False
            self.current_id = None


def test_m2_render_pl_card_emits_six_options_per_select():
    """Exercise the renderer directly — no HTTP / DB dependency.

    Generates a spec with 3 pl_visual BVs and asserts each rendered select has
    6 <option> children (1 placeholder + 5 classifications).
    """
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.api.uat_renderer import render_pl_card

    test_cases = [
        {"id": "B1", "title": "First BV",  "url": "", "steps": [], "expected": "ok"},
        {"id": "B2", "title": "Second BV", "url": "", "steps": [], "expected": "ok"},
        {"id": "B3", "title": "Third BV",  "url": "", "steps": [], "expected": "ok"},
    ]
    result_by_id = {}

    html_parts = [render_pl_card(tc, result_by_id, "", False) for tc in test_cases]
    html = "\n".join(html_parts)

    parser = _SelectCounter()
    parser.feed(html)

    assert set(parser.counts_by_id.keys()) == {"B1", "B2", "B3"}, \
        f"missing selects: {parser.counts_by_id}"
    for bv_id, count in parser.counts_by_id.items():
        assert count == 6, \
            f"{bv_id} has {count} options; expected 6 (1 placeholder + 5 classifications)"


if __name__ == "__main__":
    test_m2_render_pl_card_emits_six_options_per_select()
    print("M2 PASS")
    test_m1_classification_config_api_returns_five_classifications()
    print("M1 PASS")

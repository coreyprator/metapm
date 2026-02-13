"""
HO-BS02 — Test HO-MP01: Bulk status selected count decrements to zero.

Playwright E2E test against live MetaPM deployment.
Verifies that the bulk selection UI correctly tracks selected count
and that selecting / deselecting tasks updates the counter.

NOTE: Does NOT trigger actual bulk status changes against production.

Run: pytest tests/e2e/test_bulk_status.py -v
"""

import re
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://metapm.rentyourcio.com"


class TestBulkStatusCount:
    """Regression tests for HO-MP01: selected count must decrement to 0."""

    def test_task_rows_have_checkboxes(self, page: Page):
        """Each task row should contain a selection checkbox."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#taskList .task-row", timeout=15000)

        rows = page.locator("#taskList .task-row")
        assert rows.count() > 0, "No task rows found"

        # First row should have a checkbox
        checkbox = rows.first.locator('input[type="checkbox"]')
        assert checkbox.count() == 1, "Task row missing checkbox"

    def test_selection_count_increments_and_decrements(self, page: Page):
        """Selection count updates correctly when checking/unchecking tasks."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#taskList .task-row", timeout=15000)

        rows = page.locator("#taskList .task-row")
        if rows.count() < 2:
            pytest.skip("Need at least 2 tasks")

        selection_count = page.locator("#selectionCount")

        # Initially 0
        expect(selection_count).to_contain_text("0")

        # Check first task → count 1
        rows.nth(0).locator('input[type="checkbox"]').check()
        expect(selection_count).to_contain_text("1")

        # Check second task → count 2
        rows.nth(1).locator('input[type="checkbox"]').check()
        expect(selection_count).to_contain_text("2")

        # Uncheck first → count 1
        rows.nth(0).locator('input[type="checkbox"]').uncheck()
        expect(selection_count).to_contain_text("1")

        # Uncheck second → count 0
        rows.nth(1).locator('input[type="checkbox"]').uncheck()
        expect(selection_count).to_contain_text("0")

    def test_bulk_action_bar_initial_state(self, page: Page):
        """Bulk action bar should show 0 selected initially."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#taskList .task-row", timeout=15000)

        selection_count = page.locator("#selectionCount")
        expect(selection_count).to_contain_text("0")

        # Bulk status select and controls should exist
        bulk_select = page.locator("#bulkStatusSelect")
        assert bulk_select.count() > 0, "Bulk status dropdown not found"

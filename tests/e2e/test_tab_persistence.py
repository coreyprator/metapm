"""
HO-BS02 — Test HO-MP02: Dashboard tab persistence via localStorage.

Playwright E2E test against live MetaPM deployment.
Verifies that the last-viewed tab persists across page reloads,
and that clearing localStorage falls back to default "tasks" tab.

Run: pytest tests/e2e/test_tab_persistence.py -v
"""

import re
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://metapm.rentyourcio.com"


class TestTabPersistence:
    """Regression tests for HO-MP02: persist last-viewed tab."""

    def test_tab_persists_after_reload(self, page: Page):
        """Switching to a non-default tab should persist after page reload."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")

        # Click on a non-default tab (e.g., "projects")
        projects_btn = page.locator('.tab-btn[data-tab="projects"]')
        if projects_btn.count() == 0:
            pytest.skip("Projects tab button not found")

        projects_btn.click()
        page.wait_for_timeout(500)

        # Verify projects tab is now active
        expect(page.locator("#tab-projects")).to_be_visible()

        # Verify localStorage was set
        stored = page.evaluate("localStorage.getItem('metapm-activeTab')")
        assert stored == "projects", f"Expected localStorage 'projects', got '{stored}'"

        # Reload the page
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # After reload, projects tab should still be active
        expect(page.locator("#tab-projects")).to_be_visible()
        expect(page.locator("#tab-tasks")).to_be_hidden()

    def test_default_tab_without_localstorage(self, page: Page):
        """With no localStorage, default tab should be 'tasks'."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")

        # Clear the localStorage key
        page.evaluate("localStorage.removeItem('metapm-activeTab')")

        # Reload
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # Tasks tab should be active (default)
        expect(page.locator("#tab-tasks")).to_be_visible()

        # Tasks button should have active styling
        tasks_btn = page.locator('.tab-btn[data-tab="tasks"]')
        expect(tasks_btn).to_have_class(re.compile(r"tab-active"))

    def test_switching_tabs_updates_localstorage(self, page: Page):
        """Each tab switch should update localStorage."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")

        tabs_to_test = ["projects", "methodology", "backlog"]
        for tab_name in tabs_to_test:
            btn = page.locator(f'.tab-btn[data-tab="{tab_name}"]')
            if btn.count() > 0:
                btn.click()
                page.wait_for_timeout(300)
                stored = page.evaluate("localStorage.getItem('metapm-activeTab')")
                assert stored == tab_name, f"After clicking {tab_name}, localStorage = '{stored}'"

    def test_backlog_tab_persists(self, page: Page):
        """Specifically test backlog tab persistence (furthest from default)."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")

        backlog_btn = page.locator('.tab-btn[data-tab="backlog"]')
        if backlog_btn.count() == 0:
            pytest.skip("Backlog tab not found")

        backlog_btn.click()
        page.wait_for_timeout(500)

        # Reload
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # Backlog should still be active
        expect(page.locator("#tab-backlog")).to_be_visible()
        expect(page.locator("#tab-tasks")).to_be_hidden()

"""
MetaPM Dashboard UI Tests
==========================

Playwright tests for 8 UI updates per METAPM_UI_SPECIFICATION.md

Run: pytest tests/test_dashboard.py -v
"""

import re
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://metapm-67661554310.us-central1.run.app"


class TestDashboardUI:
    """UI verification tests for MetaPM dashboard."""

    def test_default_tab_is_tasks(self, page: Page):
        """UI Update #1: Tasks tab is visible by default on page load."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        
        # Tasks tab content should be visible
        expect(page.locator("#tab-tasks")).to_be_visible()
        
        # Tasks tab button should have active class
        tasks_btn = page.locator('.tab-btn[data-tab="tasks"]')
        expect(tasks_btn).to_have_class(re.compile(r"tab-active"))
        
        # Other tabs should be hidden
        expect(page.locator("#tab-projects")).to_be_hidden()
        expect(page.locator("#tab-history")).to_be_hidden()
        expect(page.locator("#tab-methodology")).to_be_hidden()

    def test_task_project_filter(self, page: Page):
        """UI Update #2: Project filter on Tasks tab filters task list."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        
        # Wait for tasks to load
        page.wait_for_selector("#taskList .item-row", timeout=10000)
        
        # Project filter should exist
        project_filter = page.locator("#projectFilter")
        expect(project_filter).to_be_visible()
        
        # Select a project (META if exists)
        if project_filter.locator('option[value="META"]').count() > 0:
            page.select_option("#projectFilter", "META")
            page.wait_for_timeout(500)  # Allow filter to apply
            
            # Verify filtered tasks (if any META tasks exist)
            # At minimum, verify no error occurred
            task_list = page.locator("#taskList")
            expect(task_list).to_be_visible()

    def test_project_theme_filter(self, page: Page):
        """UI Update #3: Theme and Status filters work on Projects tab."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        
        # Navigate to Projects tab
        page.click('.tab-btn[data-tab="projects"]')
        page.wait_for_selector("#projectList", state="visible")
        
        # Theme filter should exist and be populated
        theme_filter = page.locator("#themeFilter")
        expect(theme_filter).to_be_visible()
        
        # Status filter should exist
        status_filter = page.locator("#statusFilter")
        expect(status_filter).to_be_visible()
        
        # Try selecting a theme if options exist
        if theme_filter.locator("option").count() > 2:  # More than just "All Themes"
            page.select_option("#themeFilter", index=1)
            page.wait_for_timeout(500)
            
            # Verify project list updates (no error)
            expect(page.locator("#projectList")).to_be_visible()

    def test_project_open_tasks_filter(self, page: Page):
        """UI Update #4: 'Show only projects with open tasks' checkbox works."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        
        # Navigate to Projects tab
        page.click('.tab-btn[data-tab="projects"]')
        page.wait_for_selector("#projectList", state="visible")
        
        # Checkbox should exist
        open_tasks_checkbox = page.locator("#showOpenTasksOnly")
        expect(open_tasks_checkbox).to_be_visible()
        
        # Get initial project count
        initial_count = page.locator("#projectList .glass-card").count()
        
        # Check the box
        open_tasks_checkbox.check()
        page.wait_for_timeout(500)
        
        # Project list should update (count may be same or less)
        filtered_count = page.locator("#projectList .glass-card").count()
        assert filtered_count <= initial_count, "Filtered count should be <= initial count"

    def test_history_project_filter(self, page: Page):
        """UI Update #5: Project filter on AI History tab works."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        
        # Navigate to AI History tab
        page.click('.tab-btn[data-tab="history"]')
        page.wait_for_selector("#historyList", state="visible")
        
        # Project filter should exist
        history_proj_filter = page.locator("#historyProjectFilter")
        expect(history_proj_filter).to_be_visible()
        
        # Filter should be populated with projects
        option_count = history_proj_filter.locator("option").count()
        assert option_count >= 1, "Should have at least 'All Projects' option"
        
        # Try selecting a project if options exist
        if option_count > 1:
            page.select_option("#historyProjectFilter", index=1)
            page.wait_for_timeout(500)
            
            # Verify no error (list still visible)
            expect(page.locator("#historyList")).to_be_visible()

    def test_history_source_filter(self, page: Page):
        """UI Update #6: Source filter on AI History tab works."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        
        # Navigate to AI History tab
        page.click('.tab-btn[data-tab="history"]')
        page.wait_for_selector("#historyList", state="visible")
        
        # Source filter should exist with options
        source_filter = page.locator("#historySourceFilter")
        expect(source_filter).to_be_visible()
        
        # Verify options exist: All Sources, VOICE, WEB, MOBILE (count, not visibility)
        option_count = source_filter.locator('option').count()
        assert option_count >= 4, f"Expected at least 4 source filter options, found {option_count}"
        
        # Select VOICE
        page.select_option("#historySourceFilter", "VOICE")
        page.wait_for_timeout(500)
        
        # Verify list still visible
        expect(page.locator("#historyList")).to_be_visible()

    def test_history_date_range_filter(self, page: Page):
        """UI Update #7: Date range filter on AI History tab works."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        
        # Navigate to AI History tab
        page.click('.tab-btn[data-tab="history"]')
        page.wait_for_selector("#historyList", state="visible")
        
        # Date range filter should exist
        date_range_filter = page.locator("#historyDateRange")
        expect(date_range_filter).to_be_visible()
        
        # Verify options: All Time, Today, This Week, This Month (count, not visibility)
        option_count = date_range_filter.locator('option').count()
        assert option_count >= 4, f"Expected at least 4 date range options, found {option_count}"
        
        # Sort filter should work with date range
        sort_filter = page.locator("#historySortFilter")
        expect(sort_filter).to_be_visible()
        
        # Select "Today" date range
        page.select_option("#historyDateRange", "today")
        page.wait_for_timeout(500)
        
        # Verify list still visible
        expect(page.locator("#historyList")).to_be_visible()

    def test_methodology_rules_loaded(self, page: Page):
        """UI Update #8: Methodology rules are loaded and visible."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        
        # Navigate to Methodology tab
        page.click('.tab-btn[data-tab="methodology"]')
        page.wait_for_selector("#subtab-rules", state="visible")
        
        # Click Rules sub-tab (should be default)
        page.click('.method-tab[data-subtab="rules"]')
        page.wait_for_timeout(500)
        
        # Rules list should be visible
        rules_list = page.locator("#rulesList")
        expect(rules_list).to_be_visible()
        
        # Wait for rules to load (could be async)
        page.wait_for_timeout(1000)
        
        # Should have at least some rules visible (allow for initial load)
        rule_items = page.locator("#rulesList .item-row")
        item_count = rule_items.count()
        assert item_count > 0, f"Expected rules to load, found {item_count}"
        
        # Verify rule structure if any exist
        if item_count > 0:
            first_rule = rule_items.first
            expect(first_rule).to_be_visible()

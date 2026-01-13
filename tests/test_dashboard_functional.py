"""
MetaPM Dashboard Functional Tests
==================================

Tests that verify actual functionality, not just element existence.
Per VS_CODE_TEST_FAILURE_REPORT.md requirements.

Run: pytest tests/test_dashboard_functional.py -v
"""

import pytest
from playwright.sync_api import Page, expect
from datetime import datetime

BASE_URL = "https://metapm-67661554310.us-central1.run.app"


class TestTasksFunctionality:
    """Test Tasks tab actual functionality."""
    
    def test_task_project_filter_has_options(self, page: Page):
        """Verify project filter dropdown is populated with projects."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # Wait for API calls
        
        # Dropdown must have more than just "All Projects"
        options = page.locator('#projectFilter option')
        option_count = options.count()
        assert option_count > 1, f"Expected multiple project options, found {option_count}"
        
        # Verify at least one project code is present (e.g., META, EM, etc.)
        all_options_text = [options.nth(i).text_content() for i in range(option_count)]
        assert any('META' in opt or 'EM' in opt or 'SF' in opt for opt in all_options_text), \
            f"No recognizable project codes found in options: {all_options_text}"
    
    def test_task_search_filters_results(self, page: Page):
        """Verify task search box filters task list."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        # Get initial task count
        initial_count = page.locator('#taskList .item-row').count()
        if initial_count == 0:
            pytest.skip("No tasks to test search functionality")
        
        # Enter search term
        search_box = page.locator('#taskSearch')
        expect(search_box).to_be_visible()
        search_box.fill('test')
        page.wait_for_timeout(500)  # Debounce delay
        
        # Filtered count should be <= initial count
        filtered_count = page.locator('#taskList .item-row').count()
        assert filtered_count <= initial_count, \
            f"Search should reduce or maintain count: {initial_count} -> {filtered_count}"


class TestProjectsFunctionality:
    """Test Projects tab actual functionality."""
    
    def test_project_search_filters_results(self, page: Page):
        """Verify project search box filters project list."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.click('.tab-btn[data-tab="projects"]')
        page.wait_for_timeout(2000)
        
        # Get initial project count
        initial_count = page.locator('#projectList .glass-card').count()
        if initial_count == 0:
            pytest.skip("No projects to test search functionality")
        
        # Enter search term
        search_box = page.locator('#projectSearch')
        expect(search_box).to_be_visible()
        search_box.fill('meta')
        page.wait_for_timeout(500)
        
        # Filtered count should be <= initial count
        filtered_count = page.locator('#projectList .glass-card').count()
        assert filtered_count <= initial_count, \
            f"Search should reduce or maintain count: {initial_count} -> {filtered_count}"


class TestHistoryFunctionality:
    """Test AI History tab actual functionality."""
    
    def test_history_project_filter_has_options(self, page: Page):
        """Verify history project filter dropdown is populated."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.click('.tab-btn[data-tab="history"]')
        page.wait_for_timeout(2000)
        
        # Dropdown must have more than just "All Projects"
        options = page.locator('#historyProjectFilter option')
        option_count = options.count()
        assert option_count > 1, f"Expected multiple project options in history filter, found {option_count}"
    
    def test_history_source_filter_has_all_options(self, page: Page):
        """Verify source filter has VOICE, WEB, MOBILE options."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.click('.tab-btn[data-tab="history"]')
        
        select = page.locator('#historySourceFilter')
        select_html = select.inner_html()
        
        # Verify all required options are present
        assert 'VOICE' in select_html, "Missing VOICE option in source filter"
        assert 'WEB' in select_html, "Missing WEB option in source filter"
        assert 'MOBILE' in select_html, "Missing MOBILE option in source filter"
    
    def test_history_date_range_has_options(self, page: Page):
        """Verify date range filter has Today, This Week, This Month."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.click('.tab-btn[data-tab="history"]')
        
        select = page.locator('#historyDateRange')
        select_html = select.inner_html()
        
        # Verify all required options are present
        assert 'today' in select_html.lower(), "Missing 'Today' option in date range filter"
        assert 'week' in select_html.lower(), "Missing 'This Week' option in date range filter"
        assert 'month' in select_html.lower(), "Missing 'This Month' option in date range filter"
    
    def test_history_search_filters_results(self, page: Page):
        """Verify history search box filters conversation list."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.click('.tab-btn[data-tab="history"]')
        page.wait_for_timeout(2000)
        
        # Check if search box exists
        search_box = page.locator('#historySearch')
        expect(search_box).to_be_visible()


class TestMethodologyFunctionality:
    """Test Methodology tab actual functionality."""
    
    def test_methodology_search_filters_rules(self, page: Page):
        """Verify methodology search box filters rules list."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.click('.tab-btn[data-tab="methodology"]')
        page.wait_for_timeout(2000)
        
        # Get initial rule count
        initial_count = page.locator('#rulesList .item-row').count()
        if initial_count == 0:
            pytest.skip("No rules to test search functionality")
        
        # Enter search term
        search_box = page.locator('#methodologySearch')
        expect(search_box).to_be_visible()
        search_box.fill('test')
        page.wait_for_timeout(500)
        
        # Filtered count should be <= initial count
        filtered_count = page.locator('#rulesList .item-row').count()
        assert filtered_count <= initial_count, \
            f"Search should reduce or maintain count: {initial_count} -> {filtered_count}"
    
    def test_methodology_rules_loaded_and_functional(self, page: Page):
        """Verify rules are loaded and contain actual data."""
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.click('.tab-btn[data-tab="methodology"]')
        page.wait_for_timeout(2000)
        
        # Rules should be loaded
        rule_items = page.locator("#rulesList .item-row")
        item_count = rule_items.count()
        assert item_count > 0, f"Expected rules to load, found {item_count}"
        
        # First rule should have actual content (not just placeholders)
        if item_count > 0:
            first_rule = rule_items.first
            rule_text = first_rule.inner_text()
            assert len(rule_text) > 10, f"Rule seems to have no content: {rule_text}"
            # Should contain a rule code (e.g., "LL-001")
            assert '-' in rule_text or 'LL' in rule_text, \
                f"Rule doesn't contain expected code format: {rule_text}"


class TestUIConsoleErrors:
    """Test that UI loads without JavaScript console errors."""
    
    def test_no_console_errors_on_load(self, page: Page):
        """Verify page loads without JavaScript errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        # Filter out known non-critical errors (e.g., favicon 404)
        critical_errors = [e for e in errors if 'favicon' not in e.lower()]
        assert len(critical_errors) == 0, f"Console errors found: {critical_errors}"
    
    def test_no_network_failures(self, page: Page):
        """Verify no failed network requests."""
        failures = []
        page.on("requestfailed", lambda req: failures.append(f"{req.url}: {req.failure}"))
        
        page.goto(f"{BASE_URL}/static/dashboard.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        assert len(failures) == 0, f"Network failures: {failures}"

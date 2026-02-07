"""
Theme Management Tests (Playwright) - Sprint 4 Feature 2
Run: pytest tests/test_theme_management.py -v
"""

import time
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://metapm.rentyourcio.com"


def goto_dashboard(page: Page):
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)


def open_projects_tab(page: Page):
    page.click('.tab-btn[data-tab="projects"]')
    page.wait_for_timeout(1000)


class TestThemeManagement:
    def test_theme_button_visible(self, page: Page):
        """TH-001: Verify theme management button exists."""
        goto_dashboard(page)
        open_projects_tab(page)

        theme_btn = page.locator('button:has-text("Themes")')
        expect(theme_btn).to_be_visible()

    def test_theme_modal_exists(self, page: Page):
        """TH-002: Verify theme modal exists in DOM."""
        goto_dashboard(page)
        
        modal = page.locator("#themeModal")
        expect(modal).to_be_attached()

    def test_themes_list_container_exists(self, page: Page):
        """TH-003: Verify themes list container exists."""
        goto_dashboard(page)
        
        themes_list = page.locator("#themesList")
        expect(themes_list).to_be_attached()

    def test_theme_create_form_exists(self, page: Page):
        """TH-004: Verify theme creation form exists."""
        goto_dashboard(page)
        
        create_form = page.locator("#themeCreateForm")
        expect(create_form).to_be_attached()
        
        code_input = page.locator("#themeCreateCode")
        expect(code_input).to_be_attached()
        
        name_input = page.locator("#themeCreateName")
        expect(name_input).to_be_attached()

    @pytest.mark.skip(reason="API endpoint requires database connectivity - tested in integration")
    def test_theme_api_endpoint_responds(self, page: Page):
        """TH-005: Verify theme API endpoint (integration test)."""
        pass

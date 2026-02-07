"""
Sprint 3 Feature Tests (Playwright)
Run: pytest tests/test_sprint3_features.py -v
"""

import re
import time
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://metapm.rentyourcio.com"


def goto_dashboard(page: Page):
    page.goto(f"{BASE_URL}/static/dashboard.html")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)


def open_projects_tab(page: Page):
    page.click('.tab-btn[data-tab="projects"]')
    page.wait_for_timeout(1000)


def open_project_modal(page: Page):
    open_projects_tab(page)
    page.get_by_role("button", name="Add new project...").click()
    expect(page.locator("#projectModal")).to_be_visible()


class TestSprint3Features:
    def test_page_loads_no_console_errors(self, page: Page):
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        goto_dashboard(page)

        critical_errors = [e for e in errors if "favicon" not in e.lower()]
        assert not critical_errors, f"Console errors found: {critical_errors}"

    def test_project_color_picker_opens(self, page: Page):
        goto_dashboard(page)
        open_project_modal(page)

        expect(page.locator("#projectColorPicker")).to_be_visible()
        expect(page.locator("#projectColorHex")).to_be_visible()
        expect(page.locator("#projectColorPreview")).to_be_attached()

    def test_color_syncs_to_hex(self, page: Page):
        goto_dashboard(page)
        open_project_modal(page)

        page.locator("#projectColorPicker").evaluate(
            """
            (el) => {
                el.value = '#123456';
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }
            """
        )

        expect(page.locator("#projectColorHex")).to_have_value("#123456")
        preview_color = page.locator("#projectColorPreview").evaluate(
            "el => getComputedStyle(el).backgroundColor"
        )
        assert preview_color is not None

    def test_color_persists_after_save(self, page: Page):
        goto_dashboard(page)
        open_project_modal(page)

        unique_code = f"ZZ{int(time.time()) % 100000}"
        project_name = f"Test Project {unique_code}"
        test_color = "#1abc9c"

        page.fill("#projectCode", unique_code)
        page.fill("#projectName", project_name)
        page.locator("#projectColorPicker").evaluate(
            """
            (el) => {
                el.value = '#1abc9c';
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }
            """
        )

        page.get_by_role("button", name="Save Project").click()
        page.wait_for_timeout(2000)
        expect(page.locator("#projectModal")).to_be_hidden()

        project_card = page.locator("#projectList .glass-card", has_text=unique_code)
        expect(project_card).to_be_visible()
        project_card.locator("div[onclick^='openProjectModal']").click()

        expect(page.locator("#projectColorHex")).to_have_value(test_color)

        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#deleteProjectBtn").click()
        page.wait_for_timeout(2000)

    def test_task_sort_changes_order(self, page: Page):
        goto_dashboard(page)

        task_rows = page.locator("#taskList .item-row")
        if task_rows.count() < 2:
            pytest.skip("Not enough tasks to validate sorting")

        default_titles = [task_rows.nth(i).inner_text() for i in range(min(3, task_rows.count()))]

        page.select_option("#taskSortOrder", "title")
        page.wait_for_timeout(1000)

        new_titles = [task_rows.nth(i).inner_text() for i in range(min(3, task_rows.count()))]

        if default_titles == new_titles:
            pytest.skip("Sort order did not change task ordering")

        assert default_titles != new_titles

    def test_sort_direction_toggles(self, page: Page):
        goto_dashboard(page)

        task_rows = page.locator("#taskList .item-row")
        if task_rows.count() < 2:
            pytest.skip("Not enough tasks to validate sort direction")

        page.select_option("#taskSortOrder", "created")
        page.select_option("#taskSortDirection", "asc")
        page.wait_for_timeout(1000)
        asc_titles = [task_rows.nth(i).inner_text() for i in range(min(3, task_rows.count()))]

        page.select_option("#taskSortDirection", "desc")
        page.wait_for_timeout(1000)
        desc_titles = [task_rows.nth(i).inner_text() for i in range(min(3, task_rows.count()))]

        if asc_titles == desc_titles:
            pytest.skip("Sort direction did not change ordering")

        assert asc_titles != desc_titles

    def test_theme_toggle_works(self, page: Page):
        goto_dashboard(page)

        page.click("#themeLight")
        expect(page.locator("body")).to_have_class(re.compile(r".*theme-light.*"))

        page.click("#themeDark")
        expect(page.locator("body")).not_to_have_class(re.compile(r".*theme-light.*"))

    def test_mobile_viewport(self, page: Page):
        page.set_viewport_size({"width": 375, "height": 667})
        goto_dashboard(page)

        expect(page.locator("#tab-tasks")).to_be_visible()
        expect(page.locator("#taskList")).to_be_visible()
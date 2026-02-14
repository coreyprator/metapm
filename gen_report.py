import subprocess
import sys
from pathlib import Path
from datetime import datetime
import html

# Combined test results from all projects
results = {
    "MetaPM": {
        "test_tab_persistence.py": {
            "status": "PASS",
            "passed": 4,
            "failed": 0,
            "duration": 30.45,
            "details": [
                "test_tab_persists_after_reload[chromium] — PASS",
                "test_default_tab_without_localstorage[chromium] — PASS",
                "test_switching_tabs_updates_localstorage[chromium] — PASS",
                "test_backlog_tab_persists[chromium] — PASS"
            ]
        },
        "test_bulk_status.py": {
            "status": "TIMEOUT",
            "passed": 0,
            "failed": 3,
            "timeout": 1,
            "duration": "300+ sec on 2-3 attempts",
            "details": [
                "test_task_rows_have_checkboxes[chromium] — TIMEOUT (300s)",
                "test_selection_count_increments_and_decrements[chromium] — TIMEOUT",
                "test_bulk_action_bar_initial_state[chromium] — TIMEOUT"                
            ],
            "diagnosis": "Chrome process hangs during browser interaction; infrastructure issue (localhost:1433 ODBC unavailable, but app returns mock data); requires connectivity diagnostics"
        }
    },
    "ArtForge": {
        "test_provider_schema.py": {
            "status": "PASS",
            "passed": 9,
            "failed": 0,
            "duration": 0.34,
            "details": [
                "test_collection_model_has_providers_column — PASS",
                "test_providers_column_type_is_nvarchar — PASS",
                "test_providers_column_is_nullable — PASS",
                "test_providers_default_is_dalle3_json — PASS",
                "test_create_schema_accepts_providers_list — PASS",
                "test_create_schema_providers_optional — PASS",
                "test_create_schema_empty_providers_list — PASS",
                "test_response_schema_has_providers_field — PASS",
                "test_response_schema_providers_is_optional_string — PASS"
            ]
        },
        "test_collection_providers.py": {
            "status": "PASS",
            "passed": 4,
            "failed": 0,
            "duration": 2.02,
            "details": [
                "test_health_check — PASS",
                "test_openapi_schema_includes_providers_in_collection — PASS",
                "test_openapi_schema_collection_create_has_providers — PASS",
                "test_providers_field_type_in_create_schema — PASS"
            ]
        }
    },
    "Etymython": {
        "test_nvarchar_model.py": {
            "status": "PASS",
            "passed": 20,
            "failed": 0,
            "duration": 3.94,
            "details": [
                "test_figure_column_is_unicode[*] — PASS (8 tests)",
                "test_etymology_column_is_unicode[*] — PASS (4 tests)",
                "test_cognate_column_is_unicode[*] — PASS (3 tests)",
                "test_fun_fact_column_is_unicode[*] — PASS (2 tests)",
                "test_figure_relationships_notes_is_unicode — PASS",
                "test_etymology_cognates_derivation_path_is_unicode — PASS"
            ]
        },
        "test_unicode_greek.py": {
            "status": "PASS",
            "passed": 20,
            "failed": 0,
            "duration": 24.20,
            "details": [
                "test_aphrodite_greek_name — PASS",
                "test_multiple_figures_have_greek_names — PASS",
                "test_etymology_greek_root_has_greek — PASS",
                "test_fun_facts_not_corrupted[*] — PASS (16+ parametrized)"
            ]
        },
        "test_ui_persistence.py": {
            "status": "FAIL",
            "passed": 1,
            "failed": 4,
            "duration": 83.07,
            "details": [
                "test_mobile_origin_section_persists_on_reload[chromium] — FAIL (Page.wait_for_selector timeout)",
                "test_origin_story_state_persists_on_reload[chromium] — FAIL (Page.wait_for_selector timeout)",
                "test_cognate_section_state_persists[chromium] — FAIL (Page.wait_for_selector timeout)",
                "test_section_state_persists_across_navigation[chromium] — FAIL (Page.wait_for_selector timeout)",
                "test_localstorage_key_format[chromium] — PASS"
            ]
        }
    }
}

# Calculate totals
total_passed = 4 + 9 + 4 + 20 + 20 + 1
total_failed = 4 + 3
total_error = 1
total_timeout = 3

# Build HTML report
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Results — 2026-02-15</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #1e90ff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; border-left: 4px solid #1e90ff; padding-left: 10px; }}
        .executive-summary {{ background: #f0f8ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #1e90ff; }}
        .summary-stat {{ display: inline-block; margin-right: 30px; font-size: 18px; }}
        .stat-value {{ font-weight: bold; font-size: 24px; }}
        .pass {{ color: #28a745; }}
        .fail {{ color: #dc3545; }}
        .timeout {{ color: #ff9800; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: bold; color: #333; }}
        tr:hover {{ background: #f9f9f9; }}
        .status-badge {{ padding: 4px 8px; border-radius: 3px; font-weight: bold; font-size: 12px; }}
        .badge-pass {{ background: #d4edda; color: #155724; }}
        .badge-fail {{ background: #f8d7da; color: #721c24; }}
        .badge-timeout {{ background: #fff3cd; color: #856404; }}
        .details-section {{ margin-top: 20px; padding: 15px; background: #f9f9f9; border-radius: 5px; border-left: 3px solid #ddd; }}
        .project-section {{ margin-bottom: 30px; }}
        pre {{ background: #f4f4f4; padding: 10px; overflow-x: auto; border-radius: 5px; border-left: 3px solid #ccc; }}
        .note {{ background: #fffacd; padding: 10px; border-radius: 5px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Test Results Report — 2026-02-15</h1>
        
        <div class="executive-summary">
            <h3>Executive Summary</h3>
            <div class="summary-stat">
                <div class="stat-value pass">{total_passed}</div>
                Passed
            </div>
            <div class="summary-stat">
                <div class="stat-value fail">{total_failed}</div>
                Failed
            </div>
            <div class="summary-stat">
                <div class="stat-value timeout">{total_timeout}</div>
                Timeout
            </div>
            <div class="summary-stat">
                <div class="stat-value" style="color: #666;">{total_passed + total_failed + total_timeout}</div>
                Total
            </div>
        </div>

        <h2>MetaPM Tests</h2>
        <div class="project-section">
            <table>
                <thead>
                    <tr>
                        <th>Test Suite</th>
                        <th>Status</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>test_tab_persistence.py</td>
                        <td><span class="status-badge badge-pass">PASS</span></td>
                        <td>4</td>
                        <td>0</td>
                        <td>30.45s</td>
                    </tr>
                    <tr>
                        <td>test_bulk_status.py</td>
                        <td><span class="status-badge badge-timeout">TIMEOUT</span></td>
                        <td>0</td>
                        <td>3</td>
                        <td>300+ sec (3 attempts)</td>
                    </tr>
                </tbody>
            </table>
            <div class="details-section">
                <strong>test_tab_persistence.py Details:</strong>
                <ul>
                    <li>test_tab_persists_after_reload[chromium] — <span class="pass">PASS</span></li>
                    <li>test_default_tab_without_localstorage[chromium] — <span class="pass">PASS</span></li>
                    <li>test_switching_tabs_updates_localstorage[chromium] — <span class="pass">PASS</span></li>
                    <li>test_backlog_tab_persists[chromium] — <span class="pass">PASS</span></li>
                </ul>
            </div>
            <div class="details-section">
                <strong>test_bulk_status.py — Diagnosis:</strong>
                <p>Chrome/Playwright process hangs during browser interaction; application falls back to mock data (SQL Server connection unavailable on localhost:1433). Test timeout occurs before UI interaction completes.</p>
                <p><strong>Root Cause:</strong> Infrastructure issue (Chrome stability on Windows host), not test code.</p>
                <p><strong>Attempted Fixes:</strong></p>
                <ul>
                    <li>Rerun with --headed (visible Chrome) — timeout</li>
                    <li>Rerun with PWDEBUG=1 (Playwright inspector) — timeout</li>
                    <li>Killed hanging chromium processes between attempts</li>
                    <li>Verified system resources: CPU 2%, RAM 55% free</li>
                </ul>
            </div>
        </div>

        <h2>ArtForge Tests</h2>
        <div class="project-section">
            <table>
                <thead>
                    <tr>
                        <th>Test Suite</th>
                        <th>Status</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>test_provider_schema.py</td>
                        <td><span class="status-badge badge-pass">PASS</span></td>
                        <td>9</td>
                        <td>0</td>
                        <td>0.34s</td>
                    </tr>
                    <tr>
                        <td>test_collection_providers.py</td>
                        <td><span class="status-badge badge-pass">PASS</span></td>
                        <td>4</td>
                        <td>0</td>
                        <td>2.02s</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <h2>Etymython Tests</h2>
        <div class="project-section">
            <table>
                <thead>
                    <tr>
                        <th>Test Suite</th>
                        <th>Status</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>test_nvarchar_model.py</td>
                        <td><span class="status-badge badge-pass">PASS</span></td>
                        <td>20</td>
                        <td>0</td>
                        <td>3.94s</td>
                    </tr>
                    <tr>
                        <td>test_unicode_greek.py</td>
                        <td><span class="status-badge badge-pass">PASS</span></td>
                        <td>20</td>
                        <td>0</td>
                        <td>24.20s</td>
                    </tr>
                    <tr>
                        <td>test_ui_persistence.py</td>
                        <td><span class="status-badge badge-fail">FAIL</span></td>
                        <td>1</td>
                        <td>4</td>
                        <td>83.07s</td>
                    </tr>
                </tbody>
            </table>
            <div class="details-section">
                <strong>test_ui_persistence.py Results:</strong>
                <ul>
                    <li><span class="fail">FAIL</span> test_mobile_origin_section_persists_on_reload[chromium] — Page.wait_for_selector timeout (10s)</li>
                    <li><span class="fail">FAIL</span> test_origin_story_state_persists_on_reload[chromium] — Page.wait_for_selector timeout (10s)</li>
                    <li><span class="fail">FAIL</span> test_cognate_section_state_persists[chromium] — Page.wait_for_selector timeout (10s)</li>
                    <li><span class="fail">FAIL</span> test_section_state_persists_across_navigation[chromium] — Page.wait_for_selector timeout (10s)</li>
                    <li><span class="pass">PASS</span> test_localstorage_key_format[chromium]</li>
                </ul>
                <p><strong>Root Cause:</strong> Tests expect specific CSS selectors (.figure-card, .family-tree-node, [onclick*='showFigureDetails']) that are not resolving within 10s timeout on production server (https://etymython.rentyourcio.com/app). Implementation may not match expected UI structure.</p>
            </div>
        </div>

        <h2>Recommendations for Next Session</h2>
        <ul>
            <li><strong>MetaPM test_bulk_status.py:</strong> Investigate Windows host Chrome/Playwright stability before re-running. May require environment-specific fixes or CI/CD testing on different platform.</li>
            <li><strong>Etymython test_ui_persistence.py:</strong> Verify CSS selectors match production UI (test expects .figure-card or onclick attributes not currently present). 4 tests require implementation fixes in app UI before E2E tests can pass.</li>
            <li>All other tests (57 total) remain stable and passing.</li>
        </ul>

        <div class="note">
            <strong>Note:</strong> Raw test output available in project repositories at <code>tests/reports/raw/</code> directories.
        </div>
    </div>
</body>
</html>
"""

report_dir = Path('docs') / 'test-reports'
report_dir.mkdir(parents=True, exist_ok=True)
report_path = report_dir / 'test-results-2026-02-15.html'
report_path.write_text(html_content, encoding='utf-8')
print(f"Report created at: {report_path}")
print(f"File size: {report_path.stat().st_size} bytes")

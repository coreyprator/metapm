"""
ERD endpoint for MetaPM schema visualization.
MP53B Phase A.2
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

# Mermaid ERD diagram source
MERMAID_ERD = """
erDiagram
    %% Core Projects and Requirements
    roadmap_projects ||--o{ roadmap_requirements : "has"
    roadmap_projects {
        nvarchar_50 id PK
        nvarchar_20 code
        nvarchar_100 name
        nvarchar_10 emoji
        datetime2 created_at
        datetime2 updated_at
    }

    roadmap_requirements ||--o{ requirement_history : "tracks"
    roadmap_requirements ||--o{ requirement_links : "links_from"
    roadmap_requirements ||--o{ requirement_links : "links_to"
    roadmap_requirements ||--o{ requirement_dependencies : "depends_from"
    roadmap_requirements ||--o{ requirement_dependencies : "depends_to"
    roadmap_requirements {
        nvarchar_50 id PK
        nvarchar_50 project_id FK
        nvarchar_20 code
        nvarchar_200 title
        nvarchar_max description
        nvarchar_20 status
        nvarchar_5 priority
        nvarchar_20 type
        nvarchar_50 sprint_id
        nvarchar_20 pth
        datetime2 created_at
        datetime2 updated_at
        nvarchar_200 failure_class_hash "MP53B"
        nvarchar_20 bug_chain_id "MP53B"
    }

    %% Prompts and PTH Registry
    cc_prompts ||--o{ prompt_history : "tracks"
    cc_prompts {
        int id PK
        nvarchar_100 sprint_id
        nvarchar_50 project_id FK
        nvarchar_max content
        nvarchar_20 status
        nvarchar_50 version_before
        nvarchar_50 version_after
        decimal estimated_hours
        datetime2 approved_at
        nvarchar_50 approved_by
        nvarchar_50 requirement_id FK
        nvarchar_20 pth
        datetime2 created_at
        datetime2 updated_at
        nvarchar_max also_closes
        int handoff_id FK
        datetime2 session_started_at
        datetime2 session_ended_at
        nvarchar_20 session_outcome
        nvarchar_500 session_stop_reason
    }

    pth_registry {
        nvarchar_20 pth PK
        nvarchar_50 project_id FK
        datetime2 created_at
        nvarchar_50 created_by
        nvarchar_100 sprint_id
    }

    prompt_history {
        int id PK
        int prompt_id FK
        nvarchar_20 pth
        nvarchar_20 old_status
        nvarchar_20 new_status
        datetime2 changed_at
        nvarchar_100 changed_by
        nvarchar_max note
    }

    %% UAT System
    uat_pages ||--o{ uat_bv_items : "contains"
    uat_pages ||--o{ uat_results : "generates"
    uat_pages {
        nvarchar_50 id PK
        nvarchar_20 pth
        nvarchar_100 sprint_id
        nvarchar_50 project_id FK
        nvarchar_50 version
        nvarchar_max spec_data
        nvarchar_20 uat_status
        datetime2 submitted_at
        nvarchar_100 submitted_by
        nvarchar_max cai_review_json
        nvarchar_max general_notes
        datetime2 created_at
        datetime2 updated_at
    }

    uat_bv_items {
        int id PK
        nvarchar_50 spec_id FK
        nvarchar_50 bv_id
        nvarchar_200 title
        nvarchar_max expected
        nvarchar_20 bv_type
        int display_order
    }

    uat_results {
        int id PK
        nvarchar_50 spec_id FK
        nvarchar_50 requirement_id FK
        nvarchar_200 title
        nvarchar_20 status
        nvarchar_max notes
    }

    uat_classifications {
        int id PK
        nvarchar_100 name
        nvarchar_500 description
        int display_order
    }

    %% Handoffs and Reviews
    handoff_shells ||--o{ mcp_handoffs : "filled_by"
    handoff_shells ||--o{ reviews : "reviewed"
    handoff_shells {
        nvarchar_50 id PK
        nvarchar_20 pth
        nvarchar_100 sprint_id
        nvarchar_50 project_id FK
        nvarchar_50 uat_spec_id FK
        datetime2 created_at
        nvarchar_100 created_by
    }

    mcp_handoffs {
        int id PK
        nvarchar_20 pth
        nvarchar_20 direction
        nvarchar_max content
        nvarchar_500 description
        datetime2 created_at
        nvarchar_100 created_by
        nvarchar_max evidence_json
        nvarchar_50 shell_id FK
    }

    reviews {
        int id PK
        nvarchar_20 pth
        nvarchar_50 handoff_id FK
        nvarchar_20 assessment
        nvarchar_max notes
        nvarchar_max lesson_candidates
        datetime2 created_at
        nvarchar_100 created_by
    }

    %% Requirement Tracking
    requirement_history {
        int id PK
        nvarchar_50 requirement_id FK
        nvarchar_20 old_status
        nvarchar_20 new_status
        datetime2 changed_at
        nvarchar_100 changed_by
        nvarchar_500 note
    }

    requirement_links {
        int id PK
        nvarchar_50 from_requirement_id FK
        nvarchar_50 to_requirement_id FK
        nvarchar_50 link_type
        datetime2 created_at
    }

    requirement_dependencies {
        int id PK
        nvarchar_50 requirement_id FK
        nvarchar_50 depends_on_id FK
        datetime2 created_at
    }

    %% Failure Tracking
    failure_events ||--o{ failure_types : "classified_as"
    failure_events ||--o{ failure_categories : "belongs_to"
    failure_events {
        int id PK
        nvarchar_50 requirement_id FK
        nvarchar_20 pth
        nvarchar_100 sprint_id
        nvarchar_50 failure_type_id FK
        nvarchar_50 category_id FK
        nvarchar_max description
        datetime2 occurred_at
        datetime2 created_at
    }

    failure_types {
        nvarchar_50 id PK
        nvarchar_100 name
        nvarchar_500 description
        datetime2 created_at
    }

    failure_categories {
        nvarchar_50 id PK
        nvarchar_100 name
        nvarchar_500 description
        datetime2 created_at
    }

    %% Bug Chains (MP53B new table)
    bug_chains {
        nvarchar_20 id PK
        nvarchar_200 failure_class_hash
        nvarchar_200 pattern_label
        nvarchar_500 expected_outcome "MP53B"
        nvarchar_20 first_occurrence_requirement_code
        datetime2 first_occurrence_at
        nvarchar_max member_requirement_codes
        int total_occurrences
        nvarchar_20 status
        nvarchar_20 diagnostic_pth
        nvarchar_20 resolution_pth
        datetime2 resolved_at
        datetime2 created_at
        datetime2 updated_at
    }

    %% Lessons Learned
    lessons_learned {
        int id PK
        nvarchar_20 pth
        nvarchar_100 lesson
        nvarchar_50 target
        nvarchar_20 severity
        datetime2 created_at
    }

    %% Session Logs
    session_logs {
        int id PK
        nvarchar_20 pth
        nvarchar_100 session_id
        nvarchar_max transcript
        datetime2 created_at
    }

    %% Code Files
    code_files {
        int id PK
        nvarchar_50 project_id FK
        nvarchar_500 file_path
        nvarchar_max content
        nvarchar_40 file_hash
        nvarchar_40 deploy_sha
        datetime2 indexed_at
    }

    %% Templates
    templates {
        int id PK
        nvarchar_200 name
        nvarchar_500 description
        nvarchar_max content_md
        nvarchar_20 version
        datetime2 created_at
        datetime2 updated_at
        nvarchar_100 created_by
    }

    %% Compliance Docs
    compliance_docs {
        nvarchar_50 id PK
        nvarchar_20 doc_type
        nvarchar_50 project_code
        nvarchar_50 version
        nvarchar_50 checkpoint
        nvarchar_max content_md
        datetime2 updated_at
        nvarchar_100 updated_by
    }

    %% Challenge Tokens
    challenge_tokens {
        int id PK
        nvarchar_20 pth
        nvarchar_64 token
        datetime2 created_at
        bit used
        datetime2 used_at
    }

    %% Job Executions
    job_executions {
        int id PK
        nvarchar_100 job_name
        nvarchar_20 pth
        datetime2 started_at
        datetime2 completed_at
        nvarchar_20 status
        nvarchar_max output
    }

    %% MCP Tasks
    mcp_tasks {
        int id PK
        nvarchar_20 pth
        nvarchar_100 task_name
        nvarchar_20 status
        nvarchar_max metadata
        datetime2 created_at
        datetime2 updated_at
    }

    %% Orphan Audit Targets
    word_dictionary_links {
        int id PK
        nvarchar_100 word
        nvarchar_500 dictionary_url
        datetime2 created_at
    }

    staged_corrections {
        int id PK
        nvarchar_50 entity_type
        nvarchar_50 entity_id
        nvarchar_max correction_data
        datetime2 created_at
    }
"""

@router.get("/erd", response_class=HTMLResponse)
async def get_erd():
    """
    Render MetaPM ERD using Mermaid.js.
    MP53B Phase A.2 - Visual ERD at /erd on production.
    """
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MetaPM Entity Relationship Diagram</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
        }}
        .header {{
            max-width: 1400px;
            margin: 0 auto 20px auto;
            padding: 20px;
            background: #2a2a2a;
            border-radius: 8px;
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: #fff;
        }}
        .meta {{
            color: #888;
            font-size: 14px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        .mermaid {{
            background: #fff;
            padding: 20px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>MetaPM Entity Relationship Diagram</h1>
        <div class="meta">
            Generated by MP53B Phase A | Version 3.3.0 | 70 tables | Live Schema
        </div>
    </div>
    <div class="container">
        <div class="mermaid">
{MERMAID_ERD}
        </div>
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            er: {{
                useMaxWidth: true
            }}
        }});
    </script>
</body>
</html>
"""
    return html

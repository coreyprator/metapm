# Decision: Add UAT results alias endpoint

Date: 2026-02-14

## Context
UAT submissions returned a UAT id, but clients requested GET /mcp/uat/results/{id} and received 404. The canonical endpoint for a single UAT result is GET /mcp/uat/{id}.

## Options
1. Update UAT templates and clients to call GET /mcp/uat/{id} only.
2. Add an alias route for GET /mcp/uat/results/{id} to preserve existing clients.

## Decision
Add GET /mcp/uat/results/{id} as an alias to GET /mcp/uat/{id}.

## Rationale
This preserves backward compatibility for existing templates and avoids a broad client update while still using the canonical handler.

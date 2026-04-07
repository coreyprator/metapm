#!/usr/bin/env bash
# MP20 BUG-038: Reliable deploy watcher — replaces `gh run watch` which times out.
# Usage: scripts/watch-deploy.sh [run_id]
# If run_id is omitted, watches the most recent run on main.

set -euo pipefail

MAX_WAIT=600  # 10-minute ceiling
POLL_INTERVAL=30

if [ -n "${1:-}" ]; then
  RUN_ID="$1"
else
  RUN_ID=$(gh run list --limit 1 --branch main --json databaseId -q '.[0].databaseId')
  echo "Watching most recent run: $RUN_ID"
fi

ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  RESULT=$(gh run view "$RUN_ID" --json status,conclusion -q '.status + " " + (.conclusion // "pending")')
  STATUS=$(echo "$RESULT" | cut -d' ' -f1)
  CONCLUSION=$(echo "$RESULT" | cut -d' ' -f2)

  echo "[${ELAPSED}s] status=$STATUS conclusion=$CONCLUSION"

  if [ "$STATUS" = "completed" ]; then
    if [ "$CONCLUSION" = "success" ]; then
      echo "Deploy succeeded."
      exit 0
    else
      echo "Deploy failed: conclusion=$CONCLUSION"
      exit 1
    fi
  fi

  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

echo "Timed out after ${MAX_WAIT}s"
exit 1

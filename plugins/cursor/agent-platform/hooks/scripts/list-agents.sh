#!/usr/bin/env bash
# List available agents at session start when agents/ directory exists.
set -euo pipefail

AGENTS_DIR="agents"
if [[ ! -d "$AGENTS_DIR" ]]; then
  echo '{"continue": true}'
  exit 0
fi

COUNT=$(find "$AGENTS_DIR" -name '*.md' 2>/dev/null | wc -l)
if [[ $COUNT -gt 0 ]]; then
  NAMES=$(find "$AGENTS_DIR" -name '*.md' -exec basename {} .md \; | head -10 | tr '\n' ', ' | sed 's/,$//')
  echo "{\"continue\": true, \"agentMessage\": \"Agent Platform: ${COUNT} agent(s) in ${AGENTS_DIR}/ (${NAMES}). Use orchestrate skill to run multi-agent pipelines.\"}"
else
  echo '{"continue": true}'
fi

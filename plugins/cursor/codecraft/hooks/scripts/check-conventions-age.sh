#!/usr/bin/env bash
# Remind agent when CODING_REQUIREMENTS.md exists but is older than 30 days.
set -euo pipefail

INPUT=$(cat)
FILE=""
for path in .cursor/CODING_REQUIREMENTS.md docs/CODING_REQUIREMENTS.md CODING_REQUIREMENTS.md; do
  if [[ -f "$path" ]]; then
    FILE="$path"
    break
  fi
done

if [[ -z "$FILE" ]]; then
  echo '{"continue": true}'
  exit 0
fi

AGE_DAYS=$(( ($(date +%s) - $(stat -c %Y "$FILE" 2>/dev/null || stat -f %m "$FILE")) / 86400 ))
if [[ $AGE_DAYS -gt 30 ]]; then
  echo "{\"continue\": true, \"agentMessage\": \"CODING_REQUIREMENTS.md is ${AGE_DAYS} days old. Consider re-running analyze-codebase after recent architectural changes.\"}"
else
  echo '{"continue": true}'
fi

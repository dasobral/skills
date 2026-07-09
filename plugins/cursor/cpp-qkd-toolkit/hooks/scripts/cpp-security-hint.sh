#!/usr/bin/env bash
# Flag C++ edits that may need security review in QKD contexts.
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))" 2>/dev/null || echo "")

if [[ "$FILE_PATH" =~ \.(cpp|hpp|h)$ ]]; then
  if echo "$INPUT" | grep -qiE '(key|secret|password|nonce|iv|qkd|kms)' 2>/dev/null; then
    echo '{"continue": true, "agentMessage": "C++ file touches security-sensitive symbols. Consider cpp-review with --security lens before committing."}'
    exit 0
  fi
fi

echo '{"continue": true}'

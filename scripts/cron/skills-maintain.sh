#!/usr/bin/env bash
# Cron-safe wrapper: run skills-maintain with explicit PATH, logging, exit codes.
# Intended for crontab; also usable manually.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Optional local overrides (gitignored)
if [[ -f "${SCRIPT_DIR}/config.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/config.env"
  set +a
fi

SKILLS_REPO="${SKILLS_REPO:-$REPO_ROOT}"
PYTHON="${PYTHON:-/usr/bin/python3}"
LOG_FILE="${LOG_FILE:-landing/maintain.log}"
export PATH="${PATH:-/usr/local/bin:/usr/bin:/bin}"
export SHELL="${SHELL:-/bin/bash}"

cd "$SKILLS_REPO" || {
  echo "skills-cron: cannot cd to SKILLS_REPO=$SKILLS_REPO" >&2
  exit 2
}

if [[ "$LOG_FILE" != /* ]]; then
  LOG_FILE="${SKILLS_REPO}/${LOG_FILE}"
fi
mkdir -p "$(dirname "$LOG_FILE")"

MAINTAIN="${SKILLS_REPO}/bin/skills-maintain"
if [[ ! -x "$MAINTAIN" && ! -f "$MAINTAIN" ]]; then
  echo "skills-cron: missing ${MAINTAIN}" >&2
  exit 2
fi

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

{
  echo "==== $(ts) skills-maintain start ===="
  echo "repo=${SKILLS_REPO}"
  echo "python=${PYTHON} ($("$PYTHON" -V 2>&1 || true))"
  if ! "$PYTHON" -c "import yaml" 2>/dev/null; then
    echo "ERROR: PyYAML not available for ${PYTHON}" >&2
    echo "Install: pip3 install pyyaml   OR   pip3 install -e tools/skills-export" >&2
    exit 3
  fi
  set +e
  "$PYTHON" "$MAINTAIN" "$@"
  status=$?
  set -e
  echo "==== $(ts) skills-maintain end exit=${status} ===="
  exit "$status"
} >>"$LOG_FILE" 2>&1

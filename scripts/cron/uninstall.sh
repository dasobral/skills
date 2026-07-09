#!/usr/bin/env bash
# Remove the skills-maintain crontab entry installed by install.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_MARKER="# skills-framework-maintain"
DRY_RUN=0

if [[ -f "${SCRIPT_DIR}/config.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/config.env"
  set +a
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help)
      echo "Usage: $0 [--dry-run]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if ! command -v crontab >/dev/null 2>&1; then
  echo "crontab command not found" >&2
  exit 2
fi

EXISTING="$(crontab -l 2>/dev/null || true)"
if [[ -z "$EXISTING" ]]; then
  echo "No crontab entries."
  exit 0
fi

FILTERED="$(printf '%s\n' "$EXISTING" | awk -v m="$CRON_MARKER" '
  $0 == m { skip=1; next }
  skip && /^SHELL=/ { next }
  skip && /^PATH=/ { next }
  skip && /skills-maintain\.sh/ { skip=0; next }
  skip && NF==0 { next }
  { skip=0; print }
')"

if [[ "$EXISTING" == "$FILTERED" ]]; then
  echo "No skills-framework-maintain entry found."
  exit 0
fi

echo "Will remove marked cron block (${CRON_MARKER})."
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "(dry-run) remaining crontab:"
  printf '%s\n' "$FILTERED"
  exit 0
fi

if [[ -z "$(printf '%s' "$FILTERED" | tr -d '[:space:]')" ]]; then
  crontab -r 2>/dev/null || true
else
  printf '%s\n' "$FILTERED" | crontab -
fi

echo "Uninstalled. Verify with: crontab -l"

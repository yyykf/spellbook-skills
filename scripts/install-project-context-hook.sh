#!/usr/bin/env bash
set -euo pipefail

# install.py copies these siblings into a stable location, so they must be
# downloaded next to it before it runs.
files=(
  "install.py"
  "session-start"
  "project-context.md"
)

action="install"
source_dir=""
base_url="${SPELLBOOK_PC_HOOK_BASE_URL:-https://raw.githubusercontent.com/yyykf/spellbook-skills/main/hooks}"

usage() {
  cat <<'USAGE'
Install the optional Spellbook Project Context Hook for Codex and Copilot.

This wraps hooks/install.py so you can install the hook WITHOUT cloning the
repository. Claude Code does not need this — it auto-loads the plugin hook.
Only Codex / Copilot require this step.

Usage:
  install-project-context-hook.sh [install|uninstall|status]
  install-project-context-hook.sh --source ./hooks [install|uninstall|status]

Options:
  --source   Local hooks directory containing install.py and its payload files.
             If omitted, the script uses the checkout-local hooks directory
             when available, otherwise downloads from GitHub raw URLs.
  --base-url Remote base URL for downloads. Defaults to the main branch of
             yyykf/spellbook-skills.
  -h, --help Show this help.

After installing on Codex, start Codex and run /hooks once to trust the hook.
Requires python3.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    install|uninstall|status)
      action="$1"
      shift
      ;;
    --source)
      [[ $# -ge 2 ]] || { echo "--source requires a value" >&2; exit 2; }
      source_dir="$2"
      shift 2
      ;;
    --base-url)
      [[ $# -ge 2 ]] || { echo "--base-url requires a value" >&2; exit 2; }
      base_url="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run the Project Context Hook installer" >&2
  exit 1
fi

# Prefer a local checkout when present (this script lives in scripts/, hooks/ is a sibling).
if [[ -z "$source_dir" ]]; then
  script_path="${BASH_SOURCE[0]:-}"
  if [[ -n "$script_path" && -f "$script_path" ]]; then
    script_dir="$(cd "$(dirname "$script_path")" && pwd)"
    candidate_source="$(cd "$script_dir/.." && pwd)/hooks"
    if [[ -f "$candidate_source/install.py" ]]; then
      source_dir="$candidate_source"
    fi
  fi
fi

if [[ -n "$source_dir" ]]; then
  if [[ ! -f "$source_dir/install.py" ]]; then
    echo "install.py not found in source directory: $source_dir" >&2
    exit 1
  fi
  exec python3 "$source_dir/install.py" "$action"
fi

# No local checkout: download install.py and its payload into a temp dir, then run it there.
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required when no local checkout is available" >&2
  exit 1
fi

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/spellbook-pc-hook.XXXXXX")"
cleanup() { rm -rf "$work_dir"; }
trap cleanup EXIT

for file in "${files[@]}"; do
  curl -fsSL "${base_url%/}/$file" -o "$work_dir/$file"
done

python3 "$work_dir/install.py" "$action"

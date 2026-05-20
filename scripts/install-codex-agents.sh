#!/usr/bin/env bash
set -euo pipefail

files=(
  "spellbook-code-quality-reviewer.toml"
  "spellbook-code-reuse-reviewer.toml"
  "spellbook-code-efficiency-reviewer.toml"
)

scope="project"
force="false"
dry_run="false"
source_dir=""
base_url="${SPELLBOOK_CODEX_AGENTS_BASE_URL:-https://raw.githubusercontent.com/yyykf/spellbook-skills/main/codex-agents/spellbook}"

usage() {
  cat <<'USAGE'
Install Spellbook Codex agents.

Usage:
  install-codex-agents.sh [--scope project|user] [--force] [--dry-run]
  install-codex-agents.sh --source ./codex-agents/spellbook [--scope project|user]

Options:
  --scope    Install location. "project" writes ./.codex/agents/spellbook,
             "user" writes ${CODEX_HOME:-$HOME/.codex}/agents/spellbook.
             Defaults to "project".
  --source   Local directory containing the final Codex agent .toml files.
             If omitted, the script uses the checkout-local codex-agents directory
             when available, otherwise downloads from GitHub raw URLs.
  --base-url Remote base URL for downloads. Defaults to the main branch of
             yyykf/spellbook-skills.
  --force    Overwrite existing target files.
  --dry-run  Print planned actions without writing files.
  -h, --help Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope)
      [[ $# -ge 2 ]] || { echo "--scope requires a value" >&2; exit 2; }
      scope="$2"
      shift 2
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
    --force)
      force="true"
      shift
      ;;
    --dry-run)
      dry_run="true"
      shift
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

case "$scope" in
  project)
    target_dir="$PWD/.codex/agents/spellbook"
    ;;
  user)
    codex_home="${CODEX_HOME:-$HOME/.codex}"
    target_dir="$codex_home/agents/spellbook"
    ;;
  *)
    echo "--scope must be either 'project' or 'user'" >&2
    exit 2
    ;;
esac

if [[ -z "$source_dir" ]]; then
  script_path="${BASH_SOURCE[0]:-}"
  if [[ -n "$script_path" && -f "$script_path" ]]; then
    script_dir="$(cd "$(dirname "$script_path")" && pwd)"
    candidate_source="$(cd "$script_dir/.." && pwd)/codex-agents/spellbook"
    if [[ -d "$candidate_source" ]]; then
      source_dir="$candidate_source"
    fi
  fi
fi

use_local_source="false"
if [[ -n "$source_dir" ]]; then
  if [[ ! -d "$source_dir" ]]; then
    echo "source directory does not exist: $source_dir" >&2
    exit 1
  fi
  use_local_source="true"
fi

if [[ "$use_local_source" == "false" ]] && ! command -v curl >/dev/null 2>&1; then
  echo "curl is required when --source is not provided and no local checkout is available" >&2
  exit 1
fi

for file in "${files[@]}"; do
  if [[ -e "$target_dir/$file" && "$force" != "true" ]]; then
    echo "target file already exists: $target_dir/$file" >&2
    echo "rerun with --force to overwrite" >&2
    exit 1
  fi
done

if [[ "$dry_run" == "true" ]]; then
  echo "Would install Spellbook Codex agents to: $target_dir"
  exit 0
fi

mkdir -p "$target_dir"

for file in "${files[@]}"; do
  dest="$target_dir/$file"
  tmp="$(mktemp "$target_dir/.${file}.tmp.XXXXXX")"
  if [[ "$use_local_source" == "true" ]]; then
    src="$source_dir/$file"
    if [[ ! -f "$src" ]]; then
      rm -f "$tmp"
      echo "source file does not exist: $src" >&2
      exit 1
    fi
    cp "$src" "$tmp"
  else
    curl -fsSL "${base_url%/}/$file" -o "$tmp"
  fi
  mv "$tmp" "$dest"
done

echo "Installed Spellbook Codex agents to: $target_dir"

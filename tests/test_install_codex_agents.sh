#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
script="$repo_root/scripts/install-codex-agents.sh"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

assert_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "expected file to exist: $path" >&2
    exit 1
  fi
}

assert_contains() {
  local path="$1"
  local expected="$2"
  if ! grep -Fq "$expected" "$path"; then
    echo "expected $path to contain: $expected" >&2
    exit 1
  fi
}

run_project_install_copies_agents_under_project_codex_dir() {
  local project="$tmpdir/project"
  mkdir -p "$project"

  (cd "$project" && "$script" --scope project --source "$repo_root/codex-agents/spellbook")

  local target="$project/.codex/agents/spellbook"
  assert_file "$target/spellbook-code-quality-reviewer.toml"
  assert_file "$target/spellbook-code-reuse-reviewer.toml"
  assert_file "$target/spellbook-code-efficiency-reviewer.toml"
  assert_contains "$target/spellbook-code-quality-reviewer.toml" 'name = "spellbook-code-quality-reviewer"'
}

run_user_install_respects_codex_home() {
  local codex_home="$tmpdir/codex-home"

  CODEX_HOME="$codex_home" "$script" --scope user --source "$repo_root/codex-agents/spellbook"

  local target="$codex_home/agents/spellbook"
  assert_file "$target/spellbook-code-quality-reviewer.toml"
  assert_file "$target/spellbook-code-reuse-reviewer.toml"
  assert_file "$target/spellbook-code-efficiency-reviewer.toml"
}

run_existing_files_are_not_overwritten_without_force() {
  local project="$tmpdir/no-overwrite"
  local target="$project/.codex/agents/spellbook"
  mkdir -p "$target"
  printf 'local edit\n' > "$target/spellbook-code-quality-reviewer.toml"

  if (cd "$project" && "$script" --scope project --source "$repo_root/codex-agents/spellbook") >/tmp/spellbook-install.out 2>/tmp/spellbook-install.err; then
    echo "expected install to fail when target file exists without --force" >&2
    exit 1
  fi

  assert_contains "$target/spellbook-code-quality-reviewer.toml" 'local edit'
}

run_force_overwrites_existing_files() {
  local project="$tmpdir/force"
  local target="$project/.codex/agents/spellbook"
  mkdir -p "$target"
  printf 'local edit\n' > "$target/spellbook-code-quality-reviewer.toml"

  (cd "$project" && "$script" --scope project --source "$repo_root/codex-agents/spellbook" --force)

  assert_contains "$target/spellbook-code-quality-reviewer.toml" 'name = "spellbook-code-quality-reviewer"'
}

run_project_install_copies_agents_under_project_codex_dir
run_user_install_respects_codex_home
run_existing_files_are_not_overwritten_without_force
run_force_overwrites_existing_files

echo "install-codex-agents tests passed"

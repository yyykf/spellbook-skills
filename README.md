# Spellbook Skills

Personal skills library for daily workflows, packaged as Claude Code, GitHub Copilot CLI, and Codex plugins.

[中文说明](./README.zh-CN.md)

## Overview

Spellbook Skills is a collection of agent skills for daily development workflows — covering git worktrees, code review, API querying, DDD architecture guidance, and more.

## Requirements

- Claude Code v1.0.33+
- GitHub Copilot CLI for Copilot plugin, skill, and agent usage
- Codex CLI for Codex plugin and Codex agent role usage

## Install For Claude Code

Interactive Claude Code commands:

```
/plugin marketplace add yyykf/spellbook-skills
/plugin install spellbook-skills@spellbook-marketplace
/reload-plugins
```

Shell commands:

```bash
claude plugin marketplace add yyykf/spellbook-skills
claude plugin install spellbook-skills@spellbook-marketplace --scope user
```

The marketplace name is `spellbook-marketplace`, as declared by `.claude-plugin/marketplace.json`.

## Install For GitHub Copilot CLI

GitHub Copilot CLI can install the same remote marketplace and uses the Claude-compatible `.claude-plugin/plugin.json`, including both `skills/` and `agents/`.

```bash
copilot plugin marketplace add yyykf/spellbook-skills
copilot plugin install spellbook-skills@spellbook-marketplace
```

To update later:

```bash
copilot plugin marketplace update spellbook-marketplace
copilot plugin update spellbook-skills@spellbook-marketplace
```

The plugin provides the shared skills plus the reviewer agents declared in `.claude-plugin/plugin.json`.

## Install For Codex

Install the Codex plugin marketplace and plugin:

```bash
codex plugin marketplace add yyykf/spellbook-skills
codex plugin add spellbook-skills@spellbook-marketplace
```

Codex loads this plugin's skills through the plugin system, but custom reviewer agents must be installed separately as Codex agent role TOML files.
The installer uses only shell/PowerShell plus `curl` or `Invoke-WebRequest`; no Python runtime is required.

Project-scoped install, recommended for a single repository:

```bash
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-codex-agents.sh | bash
```

User-scoped install, available across repositories:

```bash
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-codex-agents.sh | bash -s -- --scope user
```

From a local checkout:

```bash
./scripts/install-codex-agents.sh --scope project
```

Windows PowerShell:

```powershell
$script = Join-Path $env:TEMP "install-codex-agents.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-codex-agents.ps1 -OutFile $script
powershell -NoProfile -ExecutionPolicy Bypass -File $script -Scope project
```

From a local checkout on Windows, `scripts/install-codex-agents.cmd` and `scripts/install-codex-agents.bat` are thin PowerShell wrappers.

The installer writes namespaced Codex roles under `agents/spellbook`:

- Project scope: `./.codex/agents/spellbook/*.toml`
- User scope: `${CODEX_HOME:-$HOME/.codex}/agents/spellbook/*.toml`

It does not overwrite existing files unless `--force` or `-Force` is provided.

## Usage

After installation, skills are namespaced by the plugin name:

```
/spellbook-skills:<skill-name>
```

## Skills

| Skill | Description |
| --- | --- |
| `using-git-worktrees-lite` | Create a worktree from the current branch with build/compile verification only (no tests) |
| `finishing-a-development-branch-lite` | Use build/compile verification as the completion gate, then merge/PR/keep/discard and clean up the worktree |
| `reviewing-gitlab-mr-comments` | Review GitLab MR comments via glab, summarize feedback, and propose a checklist or plan before execution |
| `yapi-skill` | Query YApi without running an MCP server: search interfaces and fetch interface details via Python scripts |
| `simplify` | Review changed code for reuse, quality, and efficiency with three parallel review passes, then fix issues found. Codex uses the optional namespaced reviewer agents installed above. |
| `ddd-best-practices` | DDD architecture best practices for Java/Spring Boot — layering decisions, domain modeling, code templates, test strategy, review checklists, and MVC-to-DDD migration |
| `git-merge-request` | One-shot commit + push + create merge request, supporting both GitHub Pull Requests and GitLab Merge Requests with auto-detected platform and repo-template-aware descriptions |

## Roadmap

- Add more workflow skills as they mature

## License

MIT. See [LICENSE](./LICENSE).

## Contributing

Issues and PRs are welcome. Keep changes small and focused.

## Acknowledgments

- This repository is adapted from [superpowers](https://github.com/obra/superpowers). Thanks to the original project for the skill framework and workflow design.
- The `ddd-best-practices` skill draws on ideas and practices from [xfg-ddd-skills](https://github.com/fuzhengwei/xfg-ddd-skills). Thanks for the inspiration.

# Spellbook Skills

Personal skills library for daily workflows, packaged as a Claude Code plugin.

[中文说明](./README.zh-CN.md)

## Overview

Spellbook Skills provides a minimal, reliable workflow for parallel development using git worktrees and compile-only verification.

## Features

- Worktree creation from the current branch (no test run, build/compile only)
- Completion flow that merges back to the original base branch
- Clean worktree cleanup options (merge/PR/keep/discard)

## Requirements

- Claude Code v1.0.33+

## Install (Claude Code plugin marketplace)

1. Add the marketplace:

```
/plugin marketplace add code4j/spellbook-skills
```

2. Install the plugin from the marketplace:

```
/plugin install spellbook-skills@spellbook-marketplace
```

## Usage

After installation, skills are namespaced by the plugin name:

- `/spellbook-skills:using-git-worktrees-lite`
- `/spellbook-skills:finishing-a-development-branch-lite`

## Skills

| Skill | Description |
| --- | --- |
| `using-git-worktrees-lite` | Create a worktree from the current branch with build/compile verification only (no tests) |
| `finishing-a-development-branch-lite` | Use build/compile verification as the completion gate, then merge/PR/keep/discard and clean up the worktree |
| `reviewing-gitlab-mr-comments` | Review GitLab MR comments via glab, summarize feedback, and propose a checklist or plan before execution |
| `yapi-skill` | Query YApi without running an MCP server: search interfaces and fetch interface details via Python scripts |

## Roadmap

- Add more workflow skills as they mature

## License

MIT. See [LICENSE](./LICENSE).

## Contributing

Issues and PRs are welcome. Keep changes small and focused.

## Attribution

This repository is adapted from [superpowers](https://github.com/obra/superpowers). Thanks to the original project for the workflow and skill design.

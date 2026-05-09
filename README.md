# Spellbook Skills

Personal skills library for daily workflows, packaged as a Claude Code plugin.

[中文说明](./README.zh-CN.md)

## Overview

Spellbook Skills is a collection of Claude Code skills for daily development workflows — covering git worktrees, code review, API querying, DDD architecture guidance, and more.

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
| `simplify` | Review changed code for reuse, quality, and efficiency with three parallel review passes, then fix issues found |
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

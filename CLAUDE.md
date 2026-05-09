# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## If You Are an AI Agent

Skills are not prose — they are code that shapes agent behavior. Every word in a SKILL.md influences how an agent thinks, what it prioritizes, and when it triggers. Treat skill content with the same rigor you'd apply to production code.

Before modifying any existing skill:
1. Read the full SKILL.md and all its references to understand design intent
2. Do not rewrite tone, restructure sections, or rename terminology without explicit instruction

## Project Overview

Personal skills library for Claude Code, packaged as a plugin for the Claude Code marketplace. Dual-platform support:

| Platform | Manifest | Version Strategy |
|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` | No version field, tracked by git SHA |
| Codex | `.codex-plugin/plugin.json` | Semver required |

## Repository Layout

```
skills/            All skills (one directory per skill, loaded via plugin.json "skills" field)
agents/            Shared sub-agents (e.g. code-reuse-reviewer.md, loaded via "agents" field)
scripts/           Tooling (bump-version.sh)
.claude-plugin/    Claude Code plugin manifest + marketplace config
.codex-plugin/     Codex plugin manifest
```

## Skill Authoring

Each skill is a directory under `skills/` containing:

| File | Required | Purpose |
|---|---|---|
| `SKILL.md` | Yes | YAML frontmatter (`name`, `description`) + markdown body |
| `references/` | No | Documents loaded on demand — keeps SKILL.md lean |
| `scripts/` | No | Executable scripts for deterministic/repetitive tasks |

### SKILL.md Convention

Follow this structure (adapted from superpowers):

```markdown
---
name: skill-name
description: "Trigger description with negative boundaries."
---

# Skill Title

## Overview
One-line summary.
**Core principle:** action flow in one sentence.
**Announce at start:** "I am using the X skill to ..."

## Prerequisites
- Required tools / environment / constraints

## Workflow
### Phase 1: ...
### Phase 2: ...

## Common Mistakes
- Pitfall and why it matters

## References
- [file.md](references/file.md) — description (~N lines, navigation hint)
```

### Authoring Rules

- **description must include negative boundaries**: explicitly state what the skill does NOT apply to (e.g. "not for Go/Python"), to prevent false triggers
- **Keep description concise**: aim for ~300 characters, avoid keyword-stuffing
- **Add navigation hints for large files**: for references over 300 lines, note the line count and how to navigate (e.g. "use the lookup table at top")
- **Large files need a TOC**: reference files over 300 lines must have a table of contents at the top
- **Workflow uses Phase/Step structure**: action-oriented, not an encyclopedia
- **Do not create `agents/` subdirectories inside skill directories**: shared agents go in the root `agents/` directory, not inside individual skills

## Version Management

```bash
./scripts/bump-version.sh <new-version>   # Bump all declared files to new version
./scripts/bump-version.sh --check         # Report current versions (detect drift)
./scripts/bump-version.sh --audit         # Check + grep repo for stale version strings
```

Bump the Codex plugin version when adding or changing skills (minor for new skills, patch for fixes).
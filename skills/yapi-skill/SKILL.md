---
name: yapi-skill
description: Use Python standard library scripts to directly call the Yapi API, providing interface search and detail queries (without Java/Docker/MCP Server).
---

# Yapi Search and Query Skill

## Overview

You can directly use Python scripts to call the Yapi API, search for Yapi interfaces to locate the `interfaceId`, or get detailed information of a specific interface (request parameters, response body, description in Markdown). Prefer using this skill instead of starting the `yapi-mcp-server` (Java/Docker).

**Core principle:** Configure environment -> Choose search or query details based on needs -> Execute query -> Get Markdown or JSON results.

**Announce at start:** "I am using the yapi-skill to search for or query Yapi interface details."

## Prerequisites

This skill depends on a local configuration file (`base_url` + `projectId -> token`).
If you haven't initialized it, don't know how to get the token, or need to switch between multiple environments, please read first:
- `skills/yapi-skill/references/initialization.md`

Configuration paths support the following override methods:
- Environment variable: `YAPI_SKILL_CONFIG=/path/to/config.json`
- Single command execution: `--config /path/to/config.json` (takes effect for `searchInterfaces.py` / `getInterfaceDetail.py`)

> For Windows users, if the `python3` command is not available, try using `py -3` or `python`.

## Workflow

### Step 1: Decide the Target (Search or Query Details)

Determine whether you need to first find a specific interface (using the search function) or if you already have the specific interface ID or URL to query the detailed information.

### Step 2: Execute the Query

#### Scenario A: Get Interface Details Directly (Recommended)

Use this when you already know the specific interface URL or the `projectId` and `interfaceId`.

```bash
python3 skills/yapi-skill/scripts/getInterfaceDetail.py \
  --url 'http://yapi.example.com/project/1650/interface/api/414469' \
  --format markdown
```

Description:
- `--url` supports directly pasting the interface page URL (the script will automatically parse `projectId/interfaceId`).
- `--format` supports `json` (for secondary processing) and `markdown` (for readability).
- It also supports `--projectId` + `--interfaceId` (when you already have the IDs).

> Security warning: The Markdown output may contain example request headers/example values from the interface definition (e.g., `Authorization` example). Please sanitize it yourself before sharing it externally.

#### Scenario B: Search for Interfaces (Locate interfaceId)

Use this when you only know the interface keyword or path.

```bash
python3 skills/yapi-skill/scripts/searchInterfaces.py --keyword login --format markdown
```

Common parameters:
- By default, it searches all projects in the `project_tokens` of the configuration file. (Use `--projectName` to narrow the scope).
- `--projectName`: Fuzzy filter by project name (Optional).
- `--keyword`: Fuzzy search by interface title (Optional).
- `--path`: Fuzzy search by interface path (Optional).
- `--format json|markdown`: Defaults to `json`.
- `--config <path>`: Specify the configuration file path (Overrides default path, Optional).

## Quick Reference

| Purpose | Command | Key Parameters |
| --- | --- | --- |
| Get Details | `python3 scripts/getInterfaceDetail.py` | `--url` or `--projectId`/`--interfaceId` |
| Search Interfaces | `python3 scripts/searchInterfaces.py` | `--keyword`, `--path`, `--projectName` |

## Common Mistakes

**Incomplete initialization configuration**
- **Problem:** Missing token or environment info causes request failure.
- **Fix:** Read `skills/yapi-skill/references/initialization.md` first to complete configuration.

**Sharing unsanitized Markdown**
- **Problem:** Leaking sensitive example data (e.g., real Tokens or passwords).
- **Fix:** Manually remove sensitive content from Markdown before sharing.

## Example

```bash
# Search for interfaces
python3 skills/yapi-skill/scripts/searchInterfaces.py --keyword submit_order --format markdown

# Get interface details
python3 skills/yapi-skill/scripts/getInterfaceDetail.py --url 'http://yapi.example.com/project/123/interface/api/456' --format markdown
```

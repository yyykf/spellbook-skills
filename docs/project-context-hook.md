# Project Context Hook

[中文](./project-context-hook.zh-CN.md)

At session start, automatically inject the `.project_context/` "project memory" conventions into the coding agent so it follows them throughout — capturing long-term knowledge (architecture decisions, domain terms) and process records (exploration / execution / review) into a **framework-agnostic** directory (not tied to OpenSpec / Trellis or any specific workflow framework).

The injected rules live in [`hooks/project-context.md`](../hooks/project-context.md).

## How each platform takes effect

### Claude Code ✅ automatic

Enable the plugin and you're done. Claude Code auto-discovers `hooks/hooks.json` and fires on `startup` / `clear` / `compact`. No configuration needed.

### Codex ✅ automatic (0.137.0+)

Install and enable this plugin. Codex 0.137.0+ auto-discovers the plugin-bundled `hooks/hooks.json` file and fires it on session `startup` / `clear` / `compact`.

> **⚠️ Codex requires first-time trust**: after enabling the plugin, start Codex and run `/hooks` once to review and trust this plugin hook. This is Codex's security gate and cannot be pre-trusted by a plugin or script.

### Copilot ⚙️ install once (optional)

Copilot's hook still has a compaction gap, so the installer writes the rules into personal instructions. This is an optional enhancement; skip it if you only want the plugin skills.

### Older Codex / fallback ⚙️ install once (optional)

If you are still on an older Codex release that does not auto-load plugin hooks, or you explicitly want the hook pinned into `~/.codex/hooks.json`, continue to use the installer.

**No clone required (macOS / Linux)** — the remote installer downloads `install.py` plus its payload into a temp dir and runs it. The default `install` writes Copilot instructions only; older Codex fallback must opt into the target:

```bash
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh | bash                                      # install Copilot (default)
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh | bash -s -- install --target auto            # auto-detect older Codex fallback
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh | bash -s -- install --target codex-fallback  # install older Codex fallback
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh | bash -s -- install --target all             # install Copilot + Codex fallback
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh | bash -s -- uninstall                        # uninstall all
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh | bash -s -- status
```

**No clone required (Windows PowerShell)** — the `.ps1` installer does the same:

```powershell
$script = Join-Path $env:TEMP "install-project-context-hook.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.ps1 -OutFile $script
powershell -NoProfile -ExecutionPolicy Bypass -File $script -Action install                         # Copilot (default)
powershell -NoProfile -ExecutionPolicy Bypass -File $script -Action install -Target auto            # auto-detect older Codex fallback
powershell -NoProfile -ExecutionPolicy Bypass -File $script -Action install -Target codex-fallback  # older Codex fallback
```

> Windows needs `py` / `python` / `python3` on PATH. The PowerShell installer probes candidates by actually running them, then `install.py` writes the working Python executable into Codex's hook command so runtime does not depend on a bare `python3` alias.

**From a local checkout**, run `install.py` directly (this assumes you are inside the repo checkout, where `hooks/` exists):

```bash
python3 hooks/install.py install                         # install Copilot (default)
python3 hooks/install.py install --target auto           # auto-detect older Codex fallback
python3 hooks/install.py install --target codex-fallback # install older Codex fallback
python3 hooks/install.py install --target all            # install Copilot + Codex fallback
python3 hooks/install.py uninstall                       # uninstall all (removes only what it added)
python3 hooks/install.py status                          # show install status
```

On Windows from a checkout, `scripts/install-project-context-hook.cmd` / `.bat` are thin PowerShell wrappers around `install.py`.

What `install` does:

- Copies `session-start` + `project-context.md` to a stable location `~/.local/share/spellbook-skills/hooks/` (version-independent; just re-run after upgrades)
- **Default target (Copilot)**: writes the rules into `~/.copilot/copilot-instructions.md` (personal scope, compaction-proof), wrapped in a marker block
- **`--target auto`**: runs `codex --version`; installs Codex fallback only when it confirms `< 0.137.0`, skips fallback when it confirms `>= 0.137.0`, and fails without writing config if it cannot decide
- **`--target codex-fallback`**: safely merges a SessionStart hook into `~/.codex/hooks.json`, preserving your existing hooks (e.g. codeisland)
- **`--target all`**: installs both Copilot and Codex fallback paths

`uninstall` defaults to removing all script-managed entries (by script path / marker block) without touching others; use `--target copilot` / `--target codex-fallback` to remove only one side. Repeated `install` is idempotent.

> **Re-sync after editing rules**: `project-context.md` is the single source of truth. Claude Code reads it live each session (edits take effect next session). Codex's plugin path reads the installed plugin cache, so upgrade / reinstall the plugin after editing. Codex fallback and Copilot hold a copy made at `install` time, so re-run the installer to sync them.

> Requires Python 3. Env vars `SPELLBOOK_HOME` / `CODEX_HOME` / `COPILOT_HOME` override paths (mainly for testing, see `tests/test_install.py`).

## Design notes (why it works this way)

- **Why Codex usually no longer needs manual install**: verified (codex-cli 0.137.0, 2026-06-08) that Codex auto-discovers `hooks/hooks.json` inside installed, enabled plugin bundles and lists it as `source=plugin`; first-time status is `untrusted`, so `/hooks` must trust it once. The older codex-cli 0.136.0 conclusion is stale; defer to actual runtime behavior on the target machine when expanding platform support.
- **Why Copilot uses instructions instead of a hook**: Copilot's `sessionStart` hook has no post-compaction re-injection (only `preCompact`), so rules are lost after compaction; whereas `~/.copilot/copilot-instructions.md` (personal scope, highest priority) is injected as persistent instructions, unaffected by compaction.

## Compaction behavior

| Platform | Rules kept after compaction |
|---|---|
| Claude Code | ✅ hook matcher includes `compact`, auto re-injected |
| Codex | ✅ hook matcher includes `compact`; source supports SessionStart after compaction, but still verify once with `/compact` in a long release-gate session |
| Copilot | ✅ uses instructions (compaction-proof), avoids the hook's compaction gap |

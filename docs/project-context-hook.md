# Project Context Hook

[中文](./project-context-hook.zh-CN.md)

At session start, automatically inject the `.project_context/` "project memory" conventions into the coding agent so it follows them throughout — capturing long-term knowledge (architecture decisions, domain terms) and process records (exploration / execution / review) into a **framework-agnostic** directory (not tied to OpenSpec / Trellis or any specific workflow framework).

The injected rules live in [`hooks/project-context.md`](../hooks/project-context.md).

## How each platform takes effect

### Claude Code ✅ automatic

Enable the plugin and you're done. Claude Code auto-discovers `hooks/hooks.json` and fires on `startup` / `clear` / `compact`. No configuration needed.

### Codex / Copilot ⚙️ install once (optional)

Codex does not load plugin-bundled hooks (runtime limitation, see below), and Copilot's hook has a compaction gap — so these two platforms are configured by the installer. This is an optional enhancement; skip it if you only want the plugin skills.

**No clone required (macOS / Linux)** — the remote installer downloads `install.py` plus its payload into a temp dir and runs it:

```bash
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh | bash                 # install
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh | bash -s -- uninstall
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh | bash -s -- status
```

**No clone required (Windows PowerShell)** — the `.ps1` installer does the same:

```powershell
$script = Join-Path $env:TEMP "install-project-context-hook.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.ps1 -OutFile $script
powershell -NoProfile -ExecutionPolicy Bypass -File $script install    # or: uninstall / status
```

> Windows needs `python3` / `python` / `py` on PATH. The hook command install.py writes for Codex calls `python3`, so make sure `python3` resolves at runtime (Microsoft Store Python ships a `python3` alias), or run Codex / Copilot under WSL and use the bash installer above.

**From a local checkout**, run `install.py` directly (this assumes you are inside the repo checkout, where `hooks/` exists):

```bash
python3 hooks/install.py install     # install (Codex + Copilot)
python3 hooks/install.py uninstall   # uninstall (removes only what it added)
python3 hooks/install.py status      # show install status
```

On Windows from a checkout, `scripts/install-project-context-hook.cmd` / `.bat` are thin PowerShell wrappers around `install.py`.

What `install` does:

- Copies `session-start` + `project-context.md` to a stable location `~/.local/share/spellbook-skills/hooks/` (version-independent; just re-run after upgrades)
- **Codex**: safely merges a SessionStart hook into `~/.codex/hooks.json`, preserving your existing hooks (e.g. codeisland)
- **Copilot**: writes the rules into `~/.copilot/copilot-instructions.md` (personal scope, compaction-proof), wrapped in a marker block

`uninstall` removes only its own entries (by script path / marker block) without touching others; repeated `install` is idempotent.

> **Re-sync after editing rules**: `project-context.md` is the single source of truth. Claude Code reads it live each session (edits take effect next session); but **Codex / Copilot hold a copy made at `install` time**, so after editing `project-context.md` you must **re-run the installer** (the remote installer, or `python3 hooks/install.py install` from a checkout) to sync Codex / Copilot.

> **⚠️ Codex requires first-time trust**: after `install`, start Codex and run `/hooks` once to review and trust this hook. This is Codex's security gate and cannot be pre-trusted by a script.

> Requires python3. Env vars `SPELLBOOK_HOME` / `CODEX_HOME` / `COPILOT_HOME` override paths (mainly for testing, see `tests/test_install.py`).

## Design notes (why it works this way)

- **Why Codex needs manual install**: verified (codex-cli 0.136.0, 2026-06) that Codex does not load hooks declared in the plugin manifest (the `hooks` field exists in docs but isn't executed at runtime — see [openai/codex#16430](https://github.com/openai/codex/issues/16430), [#21753](https://github.com/openai/codex/issues/21753) hook parity in progress). Defer to actual runtime behavior on newer versions.
- **Why Copilot uses instructions instead of a hook**: Copilot's `sessionStart` hook has no post-compaction re-injection (only `preCompact`), so rules are lost after compaction; whereas `~/.copilot/copilot-instructions.md` (personal scope, highest priority) is injected as persistent instructions, unaffected by compaction.

## Compaction behavior

| Platform | Rules kept after compaction |
|---|---|
| Claude Code | ✅ hook matcher includes `compact`, auto re-injected |
| Codex | hook matcher includes `compact`; documented but not locally verified ([#21675](https://github.com/openai/codex/issues/21675) still open). Verify once with `/compact` in a long session |
| Copilot | ✅ uses instructions (compaction-proof), avoids the hook's compaction gap |

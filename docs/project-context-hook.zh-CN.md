# Project Context Hook（项目记忆库规则注入）

[English](./project-context-hook.md)

会话开始和子代理启动时自动向 coding agent 注入 `.project_context/`「项目记忆库」约定，让 agent 全程遵守——把架构决策、领域术语等长期知识，以及探索 / 执行 / 审查等过程记录，沉淀到一个**框架无关**的目录里（不绑定 OpenSpec / Trellis 等具体工作流框架）。

被注入的规则正文见 [`hooks/project-context.md`](../hooks/project-context.md)。

## 各平台如何生效

### Claude Code ✅ 自动生效

启用本插件即可。Claude Code 自动发现 `hooks/hooks.json`，在 `SessionStart`（`startup` / `clear` / `compact`）和 `SubagentStart` 时触发，无需任何配置。

### Codex ✅ 自动生效（0.137.0+）

安装并启用本插件即可。Codex 0.137.0+ 会自动发现插件包内的 `hooks/hooks.json`，并在 `SessionStart`（`startup` / `clear` / `compact`）和 `SubagentStart` 时触发。

> **⚠️ Codex 首次需信任**：启动 Codex 后跑一次 `/hooks` 审核并信任本插件 hook（一次即可）。这是 Codex 的安全门控，无法由插件或脚本预信任。

### Copilot ⚙️ 安装一次（可选）

Copilot 的 hook 仍有 compact 缺陷——用安装脚本把规则写入 personal instructions。这是可选增强；只想用插件 skills 可跳过。

### Codex 旧版本 / fallback ⚙️ 安装一次（可选）

如果你仍在使用不会自动加载插件 hook 的旧 Codex，或明确想把 hook 固定安装到 `~/.codex/hooks.json`，可继续使用安装脚本。

**无需 clone 仓库（macOS / Linux）** —— 远程安装脚本会把 `install.py` 及其 payload 下载到临时目录后执行。默认 `install` 只写 Copilot instructions；旧 Codex fallback 必须显式选择 target：

```bash
script="$(mktemp)"
trap 'rm -f "$script"' EXIT
curl -fsSLo "$script" https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.sh
bash "$script" install                                      # 安装 Copilot（默认）
bash "$script" install --target auto                        # 自动判断旧 Codex fallback
bash "$script" install --target codex-fallback              # 安装旧 Codex fallback
bash "$script" install --target all                         # 同时安装 Copilot + Codex fallback
bash "$script" uninstall                                    # 卸载全部
bash "$script" status
```

**无需 clone 仓库（Windows PowerShell）** —— `.ps1` 安装脚本做同样的事：

```powershell
$script = Join-Path $env:TEMP "install-project-context-hook.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-project-context-hook.ps1 -OutFile $script
powershell -NoProfile -ExecutionPolicy Bypass -File $script -Action install                         # Copilot（默认）
powershell -NoProfile -ExecutionPolicy Bypass -File $script -Action install -Target auto            # 自动判断旧 Codex fallback
powershell -NoProfile -ExecutionPolicy Bypass -File $script -Action install -Target codex-fallback  # 旧 Codex fallback
```

> Windows 需 PATH 上有 `py` / `python` / `python3`。PowerShell 安装器会实际运行候选解释器做探测，然后由 `install.py` 把可工作的 Python 可执行文件写入 Codex hook command，因此运行时不再依赖裸 `python3` 别名。

**已 clone 仓库**时，可直接跑 `install.py`（该命令假设你在仓库 checkout 内，`hooks/` 存在）：

```bash
python3 hooks/install.py install                         # 安装 Copilot（默认）
python3 hooks/install.py install --target auto           # 自动判断旧 Codex fallback
python3 hooks/install.py install --target codex-fallback # 安装旧 Codex fallback
python3 hooks/install.py install --target all            # 同时安装 Copilot + Codex fallback
python3 hooks/install.py uninstall                       # 卸载全部（精确移除自己加的，不动他人配置）
python3 hooks/install.py status                          # 查看安装状态
```

Windows 本地 checkout 下，`scripts/install-project-context-hook.cmd` / `.bat` 是对 `install.py` 的薄 PowerShell wrapper。

`install` 做的事：

- 把 `session-start` + `project-context.md` copy 到稳定位置 `~/.local/share/spellbook-skills/hooks/`（不随插件版本号变，升级重跑即可）
- **默认 target（Copilot）**：把规则写进 `~/.copilot/copilot-instructions.md`（personal 级、抗 compact），用 marker 块包裹
- **`--target auto`**：运行 `codex --version`；只有确认 `< 0.137.0` 时才安装 Codex fallback，确认 `>= 0.137.0` 时不写 fallback，无法判断时失败且不写配置
- **`--target codex-fallback`**：把 SessionStart 和 SubagentStart hooks 安全合并进 `~/.codex/hooks.json`，保留你已有的其它 hook（如 codeisland）
- **`--target all`**：同时执行 Copilot 与 Codex fallback 两条路径

`uninstall` 默认卸载全部，靠脚本路径 / marker 块精确移除自己加的部分，不碰他人配置；也可用 `--target copilot` / `--target codex-fallback` 只卸载其中一边。重复 `install` 幂等。

> **改了规则要重新同步**：`project-context.md` 是单一真相源。Claude Code 每次会话实时读取，改了下次会话即生效；Codex 插件路径读取的是已安装插件缓存，需升级 / 重装插件后生效；Codex fallback 与 Copilot 拿到的是 `install` 时的副本，所以修改 `project-context.md` 后需**重跑安装脚本**才能同步。

> 依赖 Python 3。可用环境变量 `SPELLBOOK_HOME` / `CODEX_HOME` / `COPILOT_HOME` 覆盖路径（主要用于测试，见 `tests/test_install.py`）。

## 设计说明（为什么这样做）

- **Codex 为什么通常不再需要手动 install**：实测（codex-cli 0.137.0，2026-06-08）Codex 会自动发现已安装、已启用插件包内的 `hooks/hooks.json`，并把它列为 `source=plugin`；首次状态为 `untrusted`，需 `/hooks` 信任一次。旧结论（codex-cli 0.136.0）已过期；扩平台时仍以目标机器实际行为为准。
- **为什么显式配置 SubagentStart**：子代理使用独立生命周期事件，不依赖主会话的 SessionStart hook。这里把同一个脚本同时注册到两个事件，并让脚本返回匹配的 `hookSpecificOutput.hookEventName`，确保上下文注入到正确的会话范围。
- **Copilot 为什么用 instructions 而非 hook**：Copilot 的 `sessionStart` hook 没有 compact 后重注入机制（只有 `preCompact`），压缩后规则会丢；而 `~/.copilot/copilot-instructions.md`（personal 级、优先级最高）作为持久指令注入，不受 compact 影响，更可靠。

## compact（上下文压缩）行为

| 平台 | compact 后是否保留规则 |
|---|---|
| Claude Code | ✅ hook matcher 含 `compact`，压缩后自动重注入 |
| Codex | ✅ hook matcher 含 `compact`；源码支持 compact 后触发 SessionStart，发布前仍建议真实长会话 `/compact` 验证一次 |
| Copilot | ✅ 用 instructions（不受 compact 影响），已规避 hook 的 compact 缺陷 |

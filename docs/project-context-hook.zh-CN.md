# Project Context Hook（项目记忆库规则注入）

[English](./project-context-hook.md)

会话开始时自动向 coding agent 注入 `.project_context/`「项目记忆库」约定，让 agent 全程遵守——把架构决策、领域术语等长期知识，以及探索 / 执行 / 审查等过程记录，沉淀到一个**框架无关**的目录里（不绑定 OpenSpec / Trellis 等具体工作流框架）。

被注入的规则正文见 [`hooks/project-context.md`](../hooks/project-context.md)。

## 各平台如何生效

### Claude Code ✅ 自动生效

启用本插件即可。Claude Code 自动发现 `hooks/hooks.json`，在会话 `startup` / `clear` / `compact` 时触发，无需任何配置。

### Codex / Copilot ⚙️ 跑一次 install.py

Codex 不加载插件内 hook（运行时限制，见下），Copilot 的 hook 又有 compact 缺陷——这两个平台用安装脚本自动配置：

```bash
python3 hooks/install.py install     # 安装（Codex + Copilot）
python3 hooks/install.py uninstall   # 卸载（精确移除自己加的，不动他人配置）
python3 hooks/install.py status      # 查看安装状态
```

`install` 做的事：

- 把 `session-start` + `project-context.md` copy 到稳定位置 `~/.local/share/spellbook-skills/hooks/`（不随插件版本号变，升级重跑即可）
- **Codex**：把 SessionStart hook 安全合并进 `~/.codex/hooks.json`，保留你已有的其它 hook（如 codeisland）
- **Copilot**：把规则写进 `~/.copilot/copilot-instructions.md`（personal 级、抗 compact），用 marker 块包裹

`uninstall` 靠脚本路径 / marker 块精确移除自己加的部分，不碰他人配置；重复 `install` 幂等。

> **改了规则要重新同步**：`project-context.md` 是单一真相源。Claude Code 每次会话实时读取，改了下次会话即生效；但 **Codex / Copilot 拿到的是 `install` 时的副本**，所以修改 `project-context.md` 后需**重跑 `python3 hooks/install.py install`** 才能同步到 Codex / Copilot。

> **⚠️ Codex 首次需信任**：`install` 后启动 Codex 跑一次 `/hooks` 审核并信任本 hook（一次即可）。这是 Codex 的安全门控，无法脚本预信任。

> 依赖 python3。可用环境变量 `SPELLBOOK_HOME` / `CODEX_HOME` / `COPILOT_HOME` 覆盖路径（主要用于测试，见 `tests/test_install.py`）。

## 设计说明（为什么这样做）

- **Codex 为什么要手动 install**：实测（codex-cli 0.136.0，2026-06）Codex 不加载插件清单里的 hook（`hooks` 字段文档有、运行时未执行，见 [openai/codex#16430](https://github.com/openai/codex/issues/16430)、[#21753](https://github.com/openai/codex/issues/21753) hook parity 进行中）。**新版本以本机实际行为为准**。
- **Copilot 为什么用 instructions 而非 hook**：Copilot 的 `sessionStart` hook 没有 compact 后重注入机制（只有 `preCompact`），压缩后规则会丢；而 `~/.copilot/copilot-instructions.md`（personal 级、优先级最高）作为持久指令注入，不受 compact 影响，更可靠。

## compact（上下文压缩）行为

| 平台 | compact 后是否保留规则 |
|---|---|
| Claude Code | ✅ hook matcher 含 `compact`，压缩后自动重注入 |
| Codex | hook matcher 含 `compact`，文档支持但本机未实证（[#21675](https://github.com/openai/codex/issues/21675) 仍 open）。建议真实长会话 `/compact` 验证一次 |
| Copilot | ✅ 用 instructions（不受 compact 影响），已规避 hook 的 compact 缺陷 |

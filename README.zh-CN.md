# Spellbook Skills

面向日常工作流的个人技能仓库，提供 Claude Code 与 Codex 插件配置。

[English README](./README.md)

## 概览

Spellbook Skills 是一组面向日常开发工作流的 Claude Code 技能集合，涵盖 git worktree、代码审查、API 查询、DDD 架构指导等方面。

## 依赖

- Claude Code v1.0.33+
- Codex CLI（用于 Codex 插件与 Codex agent role）

## 安装到 Claude Code

Claude Code 交互命令：

```
/plugin marketplace add yyykf/spellbook-skills
/plugin install spellbook-skills@spellbook-marketplace
/reload-plugins
```

终端命令：

```bash
claude plugin marketplace add yyykf/spellbook-skills
claude plugin install spellbook-skills@spellbook-marketplace --scope user
```

市场名称是 `spellbook-marketplace`，由 `.claude-plugin/marketplace.json` 声明。

## 安装到 Codex

先安装 Codex 插件市场和插件：

```bash
codex plugin marketplace add yyykf/spellbook-skills
codex plugin add spellbook-skills@spellbook-marketplace
```

Codex 可以通过插件系统加载本仓库的 skills，但自定义 reviewer agents 还不能随插件自动导入，需要额外安装为 Codex agent role TOML 文件。
安装脚本只依赖 shell/PowerShell 加 `curl` 或 `Invoke-WebRequest`，不需要用户环境有 Python。

项目级安装，推荐用于单个仓库：

```bash
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-codex-agents.sh | bash
```

用户级安装，所有仓库可用：

```bash
curl -fsSL https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-codex-agents.sh | bash -s -- --scope user
```

本地仓库执行：

```bash
./scripts/install-codex-agents.sh --scope project
```

Windows PowerShell：

```powershell
$script = Join-Path $env:TEMP "install-codex-agents.ps1"
Invoke-WebRequest https://raw.githubusercontent.com/yyykf/spellbook-skills/main/scripts/install-codex-agents.ps1 -OutFile $script
powershell -NoProfile -ExecutionPolicy Bypass -File $script -Scope project
```

Windows 本地仓库里也提供了 `scripts/install-codex-agents.cmd` 和 `scripts/install-codex-agents.bat`，它们只是很薄的 PowerShell wrapper。

安装脚本会把带命名空间的 Codex roles 写到 `agents/spellbook`：

- 项目级：`./.codex/agents/spellbook/*.toml`
- 用户级：`${CODEX_HOME:-$HOME/.codex}/agents/spellbook/*.toml`

默认不会覆盖已有文件；需要覆盖时使用 `--force` 或 `-Force`。

## 使用

安装后，技能以插件名作为命名空间：

```
/spellbook-skills:<skill-name>
```

## 技能列表

| Skill | 说明 |
| --- | --- |
| `using-git-worktrees-lite` | 从当前分支创建 worktree，仅构建/编译校验（不跑测试） |
| `finishing-a-development-branch-lite` | 以构建/编译为完成门槛，按选项合并/PR/保留/丢弃并清理 worktree |
| `reviewing-gitlab-mr-comments` | 使用 glab 查看 GitLab MR 评论，汇总反馈并给出清单或计划后再执行 |
| `yapi-skill` | 免服务查询 YApi：搜索接口与获取接口详情（Python 标准库脚本直连） |
| `simplify` | 三维并行审查变更代码（复用性、质量、效率），自动修复发现的问题；Codex 可使用上面额外安装的带命名空间 reviewer agents |
| `ddd-best-practices` | DDD 架构最佳实践（Java/Spring Boot）— 分层决策、领域建模、代码模板、测试策略、审查清单与 MVC 渐进迁移 |
| `git-merge-request` | 一键提交 + 推送 + 创建合并请求，自动识别 GitHub / GitLab 远端，优先使用仓库内 PR/MR 模板 |

## 路线图

- 逐步补充更多成熟的工作流技能

## 许可证

MIT，详见 [LICENSE](./LICENSE)。

## 贡献

欢迎提交 Issue 与 PR，请保持修改范围小而明确。

## 致谢

- 本仓库参考并改写了 [superpowers](https://github.com/obra/superpowers) 的技能与流程设计，在此致谢。
- `ddd-best-practices` 技能的设计灵感与实践经验来自 [xfg-ddd-skills](https://github.com/fuzhengwei/xfg-ddd-skills)，特此致谢。

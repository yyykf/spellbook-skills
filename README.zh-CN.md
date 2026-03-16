# Spellbook Skills

面向日常工作流的个人技能仓库，提供 Claude Code 插件与市场配置。

[English README](./README.md)

## 概览

Spellbook Skills 提供最小可用的并行开发流程：基于 git worktree，且只做构建/编译校验。

## 特性

- 从当前分支创建 worktree（不跑测试，仅构建/编译）
- 以“原始基线分支”为合并目标的完成流程
- 合并/PR/保留/丢弃与 worktree 清理选项

## 依赖

- Claude Code v1.0.33+

## 安装（Claude Code 插件市场）

1. 添加市场：

```
/plugin marketplace add code4j/spellbook-skills
```

2. 安装插件：

```
/plugin install spellbook-skills@spellbook-marketplace
```

## 使用

安装后，技能以插件名作为命名空间：

- `/spellbook-skills:using-git-worktrees-lite`
- `/spellbook-skills:finishing-a-development-branch-lite`

## 技能列表

| Skill | 说明 |
| --- | --- |
| `using-git-worktrees-lite` | 从当前分支创建 worktree，仅构建/编译校验（不跑测试） |
| `finishing-a-development-branch-lite` | 以构建/编译为完成门槛，按选项合并/PR/保留/丢弃并清理 worktree |
| `reviewing-gitlab-mr-comments` | 使用 glab 查看 GitLab MR 评论，汇总反馈并给出清单或计划后再执行 |
| `yapi-skill` | 免服务查询 YApi：搜索接口与获取接口详情（Python 标准库脚本直连） |

## 路线图

- 逐步补充更多成熟的工作流技能

## 许可证

MIT，详见 [LICENSE](./LICENSE)。

## 贡献

欢迎提交 Issue 与 PR，请保持修改范围小而明确。

## 致谢

本仓库参考并改写了 [superpowers](https://github.com/obra/superpowers) 的技能与流程设计，在此致谢。

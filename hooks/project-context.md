# 项目上下文目录（.project_context）

使用项目根目录的 `.project_context/` 作为「项目记忆库」：不管用哪个 coding agent，也不管用不用 OpenSpec、Trellis 这类**工作流框架**，长期知识与过程结论都稳定沉淀在这里。

> **目录按需创建**：首次需要写入文档时，若 `.project_context/` 不存在则创建它；用不到时不必提前创建。

## 目录结构

```
.project_context/
├── design/                       # 长期知识（living·跨任务长期有效·原地维护）
│   ├── architecture/{module}/    #   架构总览 / 组件关系 / 系统约束
│   ├── decisions/{NNNN-slug}.md  #   架构决策记录（ADR），序号递增：0001、0002…
│   └── glossary/{module}.md      #   领域术语表（统一语言）
├── requirements/prd/{feature}/   # 需求源头（PRD 原件 + spec.md，默认只读）
├── explore/{module}/             # 调研结论（process）
├── plan/{module}/                # 规划笔记（process）
├── execution/{module}/           # 执行摘要（process）
│   └── {yyyy-MM-dd}_{desc}.md
└── review/{module}/              # 审查报告（process）
    └── {yyyy-MM-dd}_review_{desc}.md
```

## 两类文档，维护方式不同

- **design/（长期知识 · living）**：跨任务长期有效，**原地更新演进**。后续任务应先读这里。
  - **ADR（架构决策记录）**：一个决策一个编号文档。某决策被新决策推翻时，**不删旧文档**，而是把它的状态标记为「已被 NNNN 取代」并指向新决策——保留决策的演变史，后人能看懂"当初为什么这么定、后来为什么改"，不重复纠结同一问题。
  - **术语表**：理解深化时**就地修改完善**同一条词条，不另起"v2"、不堆叠多版本，始终保持唯一、最新。
- **explore / plan / execution / review（过程记录 · process）**：围绕单次任务，按 `yyyy-MM-dd` 命名、追加堆叠，单条价值随时间衰减。

## 与工作流框架的边界

`.project_context/` 是框架无关的记忆库，与具体工作流框架分工明确：

- **框架的工作单元产物由框架自己的目录管理，`.project_context/` 不镜像、不重复**。例如：
  - OpenSpec → `openspec/`（proposal / tasks / specs）
  - Trellis → `.trellis/`（tasks / journal）
  - Superpowers → `docs/superpowers/`（plans / specs）
- **过程文档若要关联框架的工作单元**，用 frontmatter 的 `关联:` 字段引用，**不要**用框架概念去建目录：

  ```yaml
  ---
  关联: openspec:add-auth-rbac      # 换 Trellis 时只改这行的值，如 trellis:06-03-auth-rbac
  ---
  ```

  → 目录骨架始终框架无关，换框架时记忆库连续，追溯靠引用字段保留。

## 工作流程

1. **探索**：先查 `design/`（架构/决策/术语），再查 `explore/`；无相关内容则探索并存入对应模块目录。探索中产出的**架构结论 / 关键决策 / 领域术语**，归入 `design/` 原地维护，不要混进 explore。
2. **规划**：规划笔记存入 `plan/{module}/`。
3. **执行**：执行摘要存入 `execution/{module}/`，文件名 `{yyyy-MM-dd}_{desc}.md`；关联框架产物用 `关联:` 引用字段。
4. **审查**（仅在用户明确要求「审查 / Review / 代码评审」时触发）：按 `review/review_template.md` 生成报告（含结论、核心发现、详细内容），存入 `review/{module}/`，文件名 `{yyyy-MM-dd}_review_{desc}.md`。

## 其他约定

- `requirements/prd/` 下文件默认只读，除非用户明确告知更新。
- 实现 / 调试 / 验收类任务若产生可复用过程信息，应写执行摘要，尤其是涉及代码改动、验证命令、环境状态、回退方式或验收证据时。
- 单独的 `git commit` / `git pr` / GitHub PR 包装类任务，不需要额外写执行摘要；这类任务直接在提交信息、PR 描述或最终回复中说明即可。
- 文件名统一使用英文，`{desc}` 用简短英文描述；ADR 用 `{NNNN}-{slug}.md`（序号递增、不带日期）。
- 优先复用已有探索/设计文档，避免重复工作；保持文档简洁，便于后续查阅。

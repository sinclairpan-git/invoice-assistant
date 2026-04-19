---
related_doc:
  - "docs/invoice-assistant-gap-backlog.zh-CN.md"
  - "specs/004-controlled-review-export/spec.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 实施计划：导出审计回显收口

**编号**：`009-export-audit-surface-refresh` | **日期**：2026-04-19 | **规格**：specs/009-export-audit-surface-refresh/spec.md

## 概述

本期只收口一个前端结果页缺口：导出成功后，页面不能只依赖一次性 toast，而应刷新并展示持久化导出状态。实现上采用最小范围策略，只改 `BatchResults` 与对应前端测试，不动后端导出契约。

## 技术背景

**语言/版本**：TypeScript / React  
**主要依赖**：React Router、Ant Design、Vitest  
**存储**：后端现有 SQLite + 文件系统；前端只消费既有 API  
**测试**：前端运行时 UI 测试、前端构建、AI-SDLC close-check / dry-run  
**目标平台**：本地浏览器工作台  
**约束**：

- 本轮不改后端 API、导出服务和审计落库逻辑。
- 本轮不新增导出历史页面，只在结果页补齐回显。
- 本轮优先复用 `Batch` 已有字段 `export_manifest_path` 与 `export_jobs`。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| 范围可控，避免隐式扩 scope | 只改结果页导出回显与测试，不碰后端。 |
| 先证据后结论 | 先用前端红灯测试暴露“只弹 toast、不显示持久化状态”的现状，再做最小实现。 |
| 文档与代码一致 | backlog、spec、tasks、execution log 与前端行为同步收口。 |

## 项目结构

### 文档结构

```text
specs/009-export-audit-surface-refresh/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
frontend/src/pages/BatchResults.tsx
frontend/tests/runtime-ui.test.tsx
```

## 阶段计划

### Phase 0：研究与决策冻结

**目标**：冻结 009 的真实范围，明确这是结果页导出回显缺口，而不是后端导出能力缺口。  
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md
**验证方式**：文档对账 + `python -m ai_sdlc run --dry-run`
**回退方式**：仅文档变更，可通过单次 git 回滚撤销。

### Phase 1：前端红绿收口

**目标**：导出成功后刷新并展示最近导出回显。  
**产物**：结果页刷新逻辑、最近导出区块、前端回归测试  
**验证方式**：`corepack pnpm --dir frontend test`、`corepack pnpm --dir frontend build`
**回退方式**：恢复现有 toast-only 行为；仅作为紧急回退，不保留为正式口径。

### Phase 2：归档与框架收口

**目标**：更新 backlog 和 009 work item 文档，完成 close-check 与 dry-run。  
**产物**：更新后的 backlog、tasks、execution log、development summary  
**验证方式**：`uv run ai-sdlc verify constraints`、`python -m ai_sdlc workitem close-check --wi ... --json`、`python -m ai_sdlc run --dry-run`
**回退方式**：回退本轮文档与前端改动。

## 工作流计划

### 工作流 A：结果页导出回显

**范围**：结果页导出成功后的刷新与回显  
**影响范围**：`BatchResults`、前端运行时测试  
**验证方式**：前端测试 + 前端构建  
**回退方式**：恢复导出成功后仅 toast 的行为

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| 导出成功后刷新批次详情 | 前端运行时测试 | 手工检查 `getBatch` 被重新消费 |
| 最近导出区块显示持久化路径 | 前端运行时测试 | DOM 文本断言 |
| 不引入编译问题 | 前端构建 | close-check / dry-run |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否需要新增独立导出历史页面 | 否，本轮明确不做 | 不阻塞 |
| 是否需要修改后端导出契约 | 否，本轮只消费现有字段 | 不阻塞 |

## 实施顺序建议

1. 先冻结 009 文档，明确“只改前端结果页，不改后端”。
2. 先补前端红灯测试，锁定导出成功后的刷新与回显。
3. 再做最小实现，补最近导出区块并刷新结果页。
4. 最后收口 backlog、execution log、close-check 与 dry-run。

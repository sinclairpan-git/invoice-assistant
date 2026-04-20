---
related_doc:
  - "docs/invoice-assistant-gap-backlog.zh-CN.md"
  - "specs/004-controlled-review-export/spec.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 任务分解：导出审计回显收口

**编号**：`009-export-audit-surface-refresh` | **日期**：2026-04-19
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: 文档基线冻结
Batch 2: 前端红灯与最小实现
Batch 3: 归档与框架收口
```

---

## Batch 1：文档基线冻结

### Task 1.1 冻结 009 正式范围与非目标

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md
- **可并行**：否
- **验收标准**：
  1. `spec.md` 明确这是结果页导出回显缺口，不把后端导出逻辑混入本期。
  2. `plan.md` / `tasks.md` / `task-execution-log.md` 不再保留脚手架占位文本。
- **验证**：文档对账 + `python -m ai_sdlc run --dry-run`
- **状态**：已完成

## Batch 2：前端红灯与最小实现

### Task 2.1 红灯测试锁定导出回显缺口

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：`frontend/tests/runtime-ui.test.tsx`
- **可并行**：否
- **验收标准**：
  1. 用例先暴露结果页导出成功后没有持久化回显的问题。
  2. 用例锁定“最近导出”区块与持久化路径展示。
- **验证**：`corepack pnpm --dir frontend test`
- **状态**：已完成

### Task 2.2 实现结果页导出审计回显

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：`frontend/src/pages/BatchResults.tsx`
- **可并行**：否
- **验收标准**：
  1. 任一导出成功后，结果页会刷新并读取最新批次详情。
  2. 结果页展示“最近导出”区块，并避免重复显示同一路径。
- **验证**：`corepack pnpm --dir frontend test`
- **状态**：已完成

## Batch 3：归档与框架收口

### Task 3.1 更新 backlog 与 009 work item 归档

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T22
- **文件**：`docs/invoice-assistant-gap-backlog.zh-CN.md`, `specs/009-export-audit-surface-refresh/*`
- **可并行**：否
- **验收标准**：
  1. backlog 已记录新的导出回显缺口和完成证据。
  2. 009 的 formal docs、tasks、execution log 与 development summary 同步当前实现状态。
- **验证**：文档对账 + `python -m ai_sdlc workitem close-check --wi specs/009-export-audit-surface-refresh --json`
- **状态**：已完成

### Task 3.2 完成受影响验证与 dry-run 收口

- **任务编号**：T32
- **优先级**：P1
- **依赖**：T31
- **文件**：测试与归档文件
- **可并行**：否
- **验收标准**：
  1. 前端测试和构建通过。
  2. `uv run ai-sdlc verify constraints`、`close-check` 和 `run --dry-run` 通过。
- **验证**：`corepack pnpm --dir frontend test`、`corepack pnpm --dir frontend build`、`uv run ai-sdlc verify constraints`、`python -m ai_sdlc run --dry-run`
- **状态**：已完成

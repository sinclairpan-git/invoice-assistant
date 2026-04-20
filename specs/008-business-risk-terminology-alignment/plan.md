---
related_doc:
  - "docs/invoice-assistant-gap-backlog.zh-CN.md"
  - "specs/001-invoice-assistant-mvp/spec.md"
  - "specs/004-controlled-review-export/spec.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 实施计划：业务风险分类术语回归

**编号**：`008-business-risk-terminology-alignment` | **日期**：2026-04-19 | **规格**：specs/008-business-risk-terminology-alignment/spec.md

## 概述

本期只收口一个术语漂移缺口：把当前用户可见的“业务合规”统一回上位基线裁定的“业务风险分类”。实现上采用最小 blast radius 策略，只改 UI 标签、Excel manifest 列头、受影响测试和正式规格文案，不改内部/API 键 `business_compliance_status`。

## 技术背景

**语言/版本**：Python 3.12、TypeScript  
**主要依赖**：FastAPI、React、Pytest、Vitest  
**存储**：SQLite + 本地文件系统  
**测试**：后端导出/E2E 测试、前端运行时 UI 测试、AI-SDLC `close-check` / `run --dry-run`  
**目标平台**：本地单机桌面/浏览器工作台  
**约束**：

- 本轮不改后端内部字段名 `business_compliance_status`。
- 本轮不改数据库 schema、API 响应键、规则逻辑或历史执行日志。
- 本轮以 `specs/001` 与 2026-04-17 设计文档作为 terminology source of truth。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| 范围可控、避免隐式扩 scope | 只改文案、列头、测试与规格，不碰字段名和规则逻辑。 |
| 先证据后结论 | 先补失败断言，再做最小实现，最后跑前后端回归与 dry-run。 |
| 文档与代码一致 | 同步收口当前正式规格，避免下一轮实现再次被旧 wording 拉偏。 |

## 项目结构

### 文档结构

```text
specs/008-business-risk-terminology-alignment/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
frontend/src/components/results/InvoiceDrawer.tsx
backend/app/services/export_service.py
backend/tests/test_export_service.py
backend/tests/test_end_to_end_batch.py
frontend/tests/runtime-ui.test.tsx
```

## 阶段计划

### Phase 0：研究与决策冻结

**目标**：把 008 的正式范围、非目标和 terminology source of truth 固化下来。  
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md
**验证方式**：文档对账 + `python -m ai_sdlc run --dry-run`
**回退方式**：仅文档变更，可通过单次 git 回滚撤销。

### Phase 1：用户可见术语红绿收口

**目标**：通过测试锁定详情标签和 Excel manifest 列头，统一回“业务风险分类”。  
**产物**：前端标签更新、manifest 列头更新、相关测试  
**验证方式**：`uv run pytest backend/tests/test_export_service.py backend/tests/test_end_to_end_batch.py -q`、`corepack pnpm --dir frontend test`  
**回退方式**：恢复旧文案；仅作为紧急回退，不保留为正式口径。

### Phase 2：规格文案与归档收口

**目标**：修正当前正式规格中的漂移表述，并完成 AI-SDLC 收口。  
**产物**：更新后的 `002/004` 规格、work item 文档、回归证据  
**验证方式**：`python -m ai_sdlc workitem close-check --wi ... --json`、`python -m ai_sdlc run --dry-run`
**回退方式**：回退本轮文档与文案修改。

## 工作流计划

### 工作流 A：用户可见术语统一

**范围**：详情抽屉标签、Excel manifest 列头、对应测试  
**影响范围**：前端文案、导出产物、受影响回归  
**验证方式**：前端测试 + 后端导出/E2E 测试  
**回退方式**：恢复旧文案，保留测试方便再次收口

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| 详情抽屉标签统一为“业务风险分类” | 前端测试 | 手工渲染断言 |
| Excel 列头统一为“业务风险分类” | 导出/E2E 测试 | sheet XML 文本断言 |
| 正式规格不再互相冲突 | 文档对账 | close-check / dry-run |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 是否需要重命名内部/API 键 `business_compliance_status` | 否，本轮明确不做 | 不阻塞 |
| 历史执行日志是否要重写旧术语 | 否，本轮不改历史事实 | 不阻塞 |

## 实施顺序建议

1. 先冻结 008 文档，明确“只改用户可见术语，不改内部键名”。
2. 先补失败断言，锁定详情标签与 manifest 列头。
3. 再做最小实现，更新前端标签、Excel 列头与测试。
4. 最后收口 `002/004` 正式规格、执行归档与 AI-SDLC 门禁。

---
related_doc:
  - "docs/invoice-assistant-gap-backlog.zh-CN.md"
  - "specs/004-controlled-review-export/spec.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 实施计划：导出台账字段补齐

**编号**：`007-excel-manifest-contract-completion` | **日期**：2026-04-19 | **规格**：specs/007-excel-manifest-contract-completion/spec.md

## 概述

本期只收口一个导出契约缺口：让 `excel_manifest` 的列集合追上设计基线和四期规格中已经承诺的最小台账字段。实现上优先通过红灯测试锁定缺列，再在 `ExportService` 内补最小派生逻辑，不新增 schema、不改 UI、不扩展解析器。

## 技术背景

**语言/版本**：Python 3.12  
**主要依赖**：SQLAlchemy、Pytest、zipfile/XML sheet inspection  
**存储**：SQLite + 本地文件系统  
**测试**：后端 `pytest` 导出服务与受影响回归  
**目标平台**：本地单机桌面/浏览器工作台  
**约束**：

- 本轮不新增数据库字段，只消费 `InvoiceRecord`、`ExtractedField`、`DocumentEvidence`、`ProcessingAttempt` 现有数据。
- 本轮不处理前端术语统一，也不扩展导出文件类型。
- 允许部分列在数据缺失时输出空字符串，但不允许因为缺字段而导出失败。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| 本地优先、可解释自动化 | 直接补齐本地 manifest 契约，让导出文件本身承载解释信息，而不是依赖额外系统。 |
| 小步迭代、范围可控 | 只触达 `export_service.py` 和导出测试，不修改解析管线与前端。 |
| 先证据后结论 | 先写红灯测试断言缺列，再做最小实现并复跑定向回归。 |

## 项目结构

### 文档结构

```text
specs/007-excel-manifest-contract-completion/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
backend/
├── app/services/export_service.py
├── app/api/serializers.py
└── tests/test_export_service.py
```

## 阶段计划

### Phase 0：研究与决策冻结

**目标**：冻结 007 的正式范围、非目标和字段来源边界，避免把术语统一或新解析能力混入本期。  
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md
**验证方式**：文档对账 + `python -m ai_sdlc run --dry-run`
**回退方式**：仅文档变更，可通过单次 git 回滚撤销。

### Phase 1：manifest 契约红绿收口

**目标**：用红灯测试锁定缺失列，并在导出服务内补齐最小派生逻辑。
**产物**：manifest 列补齐实现、导出测试
**验证方式**：`uv run pytest backend/tests/test_export_service.py -q`
**回退方式**：恢复旧 manifest 列集合；仅作为紧急回退，不保留为正式导出契约。

### Phase 2：受影响回归与归档

**目标**：确认四期导出摘要与端到端主路径不回退，并完成 formal docs 归档。
**产物**：更新后的任务状态、执行日志、必要回归证据
**验证方式**：导出服务测试 + 受影响端到端/API 回归 + `python -m ai_sdlc run --dry-run`
**回退方式**：回退本轮代码与归档修改，恢复到补齐前状态。

## 工作流计划

### 工作流 A：manifest 列头与值补齐

**范围**：`ExportService._write_excel_manifest()` 及其辅助派生函数  
**影响范围**：导出台账列集合、sheet XML 内容、现有导出测试  
**验证方式**：`backend/tests/test_export_service.py`  
**回退方式**：回退列补齐实现，恢复旧台账列集合

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| manifest 新增列头存在 | 导出服务测试 | XML sheet 文本断言 |
| 扩展字段值来源稳定 | 导出服务测试 | 人工构造 `ExtractedField` / `ProcessingAttempt` |
| 导出摘要与门槛不回退 | 既有导出测试 + API/E2E 回归 | `run --dry-run` |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| `发票明细摘要` 优先取 `table_lines` 还是 `text_blocks` | 倾向 `table_lines` 优先，缺失时回退 `text_blocks` | Phase 1 |
| `处理时间` 是否应取最新 attempt 完成时间 | 倾向是 | Phase 1 |

## 实施顺序建议

1. 先冻结 007 文档和 backlog 真值，明确“只补 manifest 列，不扩解析器”。
2. 先写导出服务红灯测试，覆盖新增列头和代表性列值。
3. 再在 `ExportService` 内补最小派生逻辑，优先复用现有落库字段和证据文本。
4. 最后跑导出服务、受影响回归与 `python -m ai_sdlc run --dry-run`，并补归档。

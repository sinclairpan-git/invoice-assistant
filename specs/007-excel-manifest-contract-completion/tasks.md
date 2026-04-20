---
related_doc:
  - "docs/invoice-assistant-gap-backlog.zh-CN.md"
  - "specs/004-controlled-review-export/spec.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 任务分解：导出台账字段补齐

**编号**：`007-excel-manifest-contract-completion` | **日期**：2026-04-19
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: 文档基线冻结
Batch 2: manifest 契约红灯与最小实现
Batch 3: 回归验证与归档
```

---

## Batch 1：文档基线冻结

### Task 1.1 冻结 007 正式范围与字段来源边界

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md
- **可并行**：否
- **验收标准**：
  1. `spec.md` 明确列补齐范围、非目标、字段来源与成功标准。
  2. 007 不再保留脚手架占位文本，也不把术语统一混入本期。
- **验证**：文档对账
- **状态**：已完成

## Batch 2：manifest 契约红灯与最小实现

### Task 2.1 红灯测试锁定 manifest 缺失列

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：`backend/tests/test_export_service.py`
- **可并行**：否
- **验收标准**：
  1. 新增用例先暴露 `excel_manifest` 缺少目标列头和值的问题。
  2. 用例覆盖至少一条普通票和一条重复票的 manifest 值断言。
- **验证**：`uv run pytest backend/tests/test_export_service.py::test_excel_manifest_includes_required_contract_columns -q`
- **状态**：已完成

### Task 2.2 实现 manifest 列补齐最小逻辑

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：`backend/app/services/export_service.py`
- **可并行**：否
- **验收标准**：
  1. manifest 补齐 10 个目标列头。
  2. 列值来源优先复用现有落库字段、提取字段、证据文本与 attempt 时间，不新增 schema。
  3. 现有导出摘要、门槛与附件列不回退。
- **验证**：`uv run pytest backend/tests/test_export_service.py -q`
- **状态**：已完成

## Batch 3：回归验证与归档

### Task 3.1 完成受影响回归与 dry-run 收口

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T22
- **文件**：测试与文档归档文件
- **可并行**：否
- **验收标准**：
  1. 导出服务与受影响端到端路径通过回归。
  2. `python -m ai_sdlc run --dry-run` 继续通过，不因 007 引入新的 close blocker。
- **验证**：`uv run pytest backend/tests/test_export_service.py backend/tests/test_end_to_end_batch.py::test_end_to_end_batch_upload_to_export_keeps_ui_export_and_db_consistent -q`，`python -m ai_sdlc run --dry-run`
- **状态**：已完成

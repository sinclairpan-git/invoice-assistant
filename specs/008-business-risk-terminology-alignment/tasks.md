---
related_doc:
  - "docs/invoice-assistant-gap-backlog.zh-CN.md"
  - "specs/001-invoice-assistant-mvp/spec.md"
  - "specs/004-controlled-review-export/spec.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 任务分解：业务风险分类术语回归

**编号**：`008-business-risk-terminology-alignment` | **日期**：2026-04-19
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: 文档基线冻结
Batch 2: 用户可见术语红灯与最小实现
Batch 3: 规格收口与验证归档
```

---

## Batch 1：文档基线冻结

### Task 1.1 冻结 008 正式范围与术语来源

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md
- **可并行**：否
- **验收标准**：
  1. `spec.md` 明确 authoritative terminology、覆盖范围和非目标。
  2. 008 不再保留脚手架占位文本，也不把字段名重命名混入本期。
- **验证**：文档对账
- **状态**：已完成

## Batch 2：用户可见术语红灯与最小实现

### Task 2.1 红灯测试锁定“业务风险分类”用户可见面

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：`backend/tests/test_export_service.py`, `backend/tests/test_end_to_end_batch.py`, `frontend/tests/runtime-ui.test.tsx`
- **可并行**：否
- **验收标准**：
  1. 用例先暴露详情标签或 Excel 列头仍显示“业务合规”的问题。
  2. 用例覆盖前端详情与 manifest 两个用户可见面。
- **验证**：`uv run pytest backend/tests/test_export_service.py::test_export_service_blocks_pending_review_pass_export_and_success_manifest_includes_compliance_fields backend/tests/test_end_to_end_batch.py::test_end_to_end_batch_upload_to_export_keeps_ui_export_and_db_consistent -q`，`corepack pnpm --dir frontend test`
- **状态**：已完成

### Task 2.2 实现最小术语回归

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：`frontend/src/components/results/InvoiceDrawer.tsx`, `backend/app/services/export_service.py`
- **可并行**：否
- **验收标准**：
  1. 详情标签和 Excel 列头统一为“业务风险分类”。
  2. 内部/API 键 `business_compliance_status` 保持不变。
- **验证**：与 T21 相同
- **状态**：已完成

## Batch 3：规格收口与验证归档

### Task 3.1 更新正式规格与归档

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T22
- **文件**：`specs/002-invoice-assistant-runtime-hardening/spec.md`, `specs/004-controlled-review-export/spec.md`, `docs/invoice-assistant-gap-backlog.zh-CN.md`, `specs/008-business-risk-terminology-alignment/*`
- **可并行**：否
- **验收标准**：
  1. `002/004` 当前正式规格不再出现与 `001/design` 冲突的用户可见术语。
  2. backlog 与 008 执行归档同步当前裁决和验证证据。
- **验证**：文档对账 + `python -m ai_sdlc workitem close-check --wi specs/008-business-risk-terminology-alignment --json`
- **状态**：已完成

### Task 3.2 完成受影响回归与 dry-run 收口

- **任务编号**：T32
- **优先级**：P1
- **依赖**：T31
- **文件**：测试与文档归档文件
- **可并行**：否
- **验收标准**：
  1. 前后端受影响回归通过。
  2. `python -m ai_sdlc run --dry-run` 继续通过。
- **验证**：`uv run pytest backend/tests/test_export_service.py backend/tests/test_end_to_end_batch.py -q`，`corepack pnpm --dir frontend test`，`corepack pnpm --dir frontend build`，`python -m ai_sdlc run --dry-run`
- **状态**：已完成
